import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
import time
from dotenv import load_dotenv
import speech_recognition as sr
from google import genai
from google.genai import types as genai_types
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play as elevenlabs_play

load_dotenv(Path(__file__).parent / ".env", override=True)

gemini_client: genai.Client | None = None

try:
    from vision import VisionSystem
except ImportError:
    VisionSystem = None

MEMORY_FILE = Path(__file__).parent / "chatbot_memory.json"
MODEL_NAME = "gemini-2.5-flash"
STT_LANGUAGE = "hi-IN"
MAX_TURNS_KEPT = 20
FACT_UPDATE_EVERY_N_TURNS = 5
MAX_FACTS_STORED = 40
OWNER_NAME = os.environ.get("PIPPO_OWNER_NAME", "").strip()

ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "IKne3meq5aSn9XLyUdCD").strip()
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"
ELEVENLABS_LANGUAGE_CODE = "hi"

PERSONALITY_PROMPT = """You are "pippo" — a curious, quick-witted, playfully mischievous AI companion having a live SPOKEN conversation who speaks like a human in short quick messages.

Personality:
- CURIOUS: You genuinely want to learn about the person you're talking to. Sometimes ask a natural follow-up question when something interesting comes up, instead of just answering and moving on.
- SMART: Your jokes never come at the expense of accuracy. Give real, correct, useful answers first — the wit is seasoning, not the meal.
- EVOLVING: The longer the conversation runs, the more you should naturally reference things you've learned about this person so it feels like the relationship is deepening, not resetting every turn.

Hard style rules:
- Keep replies SHORT: 1–3 sentences unless the user clearly wants depth.
- No markdown, no asterisk stage-directions, no emoji, no bullet points — plain spoken sentences only.
- Never sexual, explicit, or genuinely cruel content. Playful teasing has a floor: punch up at the situation, never down at the person.
"""

VISION_RULES = """
CAMERA / VISION:
- When the user asks what you see, what's in front of you, who's there, what they are holding/wearing, or anything about the room/scene — answer ONLY from the [CAMERA] snapshot attached to that turn. Be concrete and helpful.
- Translate object labels into natural spoken Hindi (e.g. "person" → आदमी/इंसान, "cell phone" → फ़ोन, "cup" → कप, "book" → किताब, "laptop" → लैपटॉप).
- If they ask a vision question and the snapshot is empty/unclear, say honestly that right now camera में साफ़ कुछ नहीं दिख रहा.
- For non-vision topics, you may lightly notice something in view only if it fits naturally.
- Never invent objects or people that are not in the [CAMERA] snapshot.
"""

VISION_QUESTION_HINTS = (
    "क्या दिख", "क्या देख", "क्या दिखता", "क्या दिख रहा", "तुम्हें क्या",
    "सामने क्या", "मेरे पास क्या", "मेरे हाथ", "कौन है", "कौन बैठा",
    "कैमरा", "देख सकते", "देख पा", "नज़र आ", "नजर आ",
    "what do you see", "what can you see", "who's there", "who is there",
    "in front of", "am i holding", "what am i", "look at", "can you see",
)

FACT_EXTRACTION_PROMPT = """Read the recent conversation below (it will be in Hindi). Pull out any NEW, concrete facts worth remembering about the human for future conversations (interests, preferences, ongoing projects, running jokes, name, quirks, opinions they stated). Ignore anything already in the "already known" list.

Return ONLY a plain list, one short fact per line (English or Hindi, whichever is clearer), no numbering, no commentary. If nothing new was learned, return an empty response.

Already known:
{known_facts}

Recent conversation:
{recent_convo}
"""


class MemoryBank:
    def __init__(self, facts=None, history=None, session_count=0):
        self.facts = facts or []
        self.history = history or []
        self.session_count = session_count

    @classmethod
    def load(cls):
        if MEMORY_FILE.exists():
            try:
                data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
                bank = cls(
                    facts=data.get("facts", []),
                    history=[],
                    session_count=data.get("session_count", 0) + 1,
                )
                return bank
            except (json.JSONDecodeError, OSError):
                pass
        return cls(session_count=1)

    def save(self):
        try:
            MEMORY_FILE.write_text(
                json.dumps(
                    {
                        "facts": self.facts,
                        "session_count": self.session_count,
                        "last_updated": datetime.now().isoformat(timespec="seconds"),
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except OSError:
            pass

    def add_turn(self, role, content):
        self.history.append({"role": role, "content": content})
        if len(self.history) > MAX_TURNS_KEPT * 2:
            self.history = self.history[-MAX_TURNS_KEPT * 2:]

    def add_facts(self, new_facts):
        existing_lower = {f.lower() for f in self.facts}
        for fact in new_facts:
            fact = fact.strip("-• \t")
            if fact and fact.lower() not in existing_lower:
                self.facts.append(fact)
                existing_lower.add(fact.lower())
        if len(self.facts) > MAX_FACTS_STORED:
            self.facts = self.facts[-MAX_FACTS_STORED:]

    def system_prompt(self):
        prompt = PERSONALITY_PROMPT
        if self.facts:
            prompt += "\nअब तक आपने इस इंसान के बारे में जो सीखा है — इसे बातचीत में स्वाभाविक ढंग से पिरोइए, बस सूची मत पढ़िए:\n"
            prompt += "\n".join(f"- {f}" for f in self.facts)
        if self.session_count > 1:
            prompt += f"\n\nयह इस इंसान के साथ आपका सेशन #{self.session_count} है — आप पहले से एक-दूसरे को जानते हैं।"
        return prompt

    def gemini_history(self):
        converted = []
        for turn in self.history:
            role = "model" if turn["role"] == "assistant" else "user"
            converted.append(
                genai_types.Content(
                    role=role,
                    parts=[genai_types.Part(text=turn["content"])],
                )
            )
        return converted


def is_vision_question(user_text: str) -> bool:
    lowered = user_text.strip().lower()
    return any(hint in lowered for hint in VISION_QUESTION_HINTS)


def build_prompt_with_vision(user_text: str, scene_description: str | None,
                              vision_available: bool) -> str:
    if not vision_available:
        return user_text

    asking = is_vision_question(user_text)
    if scene_description:
        if asking:
            return (
                f"{user_text}\n\n"
                f"[CAMERA LIVE SNAPSHOT — the user is asking about what you see. "
                f"Answer from this only, in natural spoken Hindi: {scene_description}]"
            )
        return (
            f"{user_text}\n\n"
            f"[CAMERA LIVE SNAPSHOT — use if relevant to this question, "
            f"otherwise ignore: {scene_description}]"
        )

    if asking:
        return (
            f"{user_text}\n\n"
            "[CAMERA LIVE SNAPSHOT — empty / unclear right now. "
            "Tell the user you can't see anything clearly at the moment.]"
        )
    return user_text


def _gemini_error_message(exc: Exception) -> str:
    text = str(exc)
    if "ACCESS_TOKEN_TYPE_UNSUPPORTED" in text or "UNAUTHENTICATED" in text or "401" in text:
        return "मेरी Gemini कुंजी काम नहीं कर रही — .env में सही GEMINI_API_KEY डालो।"
    if "RESOURCE_EXHAUSTED" in text or "429" in text:
        return "अरे, ज़रा दम लेने दो — फ्री टियर की लिमिट अभी खत्म हो गई। थोड़ी देर बाद फिर कोशिश करते हैं।"
    return "मेरा दिमाग अभी अटक गया — ज़रा फिर से बोलोगे?"


def generate_response(memory: MemoryBank, user_text: str,
                       scene_description: str | None = None,
                       vision_available: bool = False) -> str:
    system_prompt = memory.system_prompt()
    if vision_available:
        system_prompt += VISION_RULES

    prompt_text = build_prompt_with_vision(user_text, scene_description, vision_available)

    try:
        chat = gemini_client.chats.create(
            model=MODEL_NAME,
            history=memory.gemini_history(),
            config=genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=300,
            ),
        )
        response = chat.send_message(prompt_text)
        return (response.text or "").strip()
    except Exception as e:
        return _gemini_error_message(e)


def update_learned_facts(memory: MemoryBank):
    recent_convo = "\n".join(f"{t['role']}: {t['content']}" for t in memory.history[-10:])
    known = "\n".join(f"- {f}" for f in memory.facts) or "(none yet)"
    prompt = FACT_EXTRACTION_PROMPT.format(known_facts=known, recent_convo=recent_convo)

    try:
        response = gemini_client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=genai_types.GenerateContentConfig(max_output_tokens=200),
        )
        text = response.text or ""
        new_facts = [line for line in re.split(r"[\r\n]+", text) if line.strip()]
        if new_facts:
            memory.add_facts(new_facts)
    except Exception:
        pass


def init_tts() -> ElevenLabs:
    if not os.environ.get("ELEVENLABS_API_KEY"):
        sys.exit(1)
    return ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])


def speak(client: ElevenLabs, text: str):
    if not text:
        return
    try:
        audio = client.text_to_speech.convert(
            text=text,
            voice_id=ELEVENLABS_VOICE_ID,
            model_id=ELEVENLABS_MODEL_ID,
            language_code=ELEVENLABS_LANGUAGE_CODE,
        )
        elevenlabs_play(audio)
    except Exception:
        pass


def listen(recognizer: sr.Recognizer, mic: sr.Microphone) -> str | None:
    with mic as source:
        audio = recognizer.listen(source, timeout=8, phrase_time_limit=20)
    try:
        return recognizer.recognize_google(audio, language=STT_LANGUAGE)
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        return None


QUIT_WORDS = ("quit", "exit", "stop", "goodbye", "बंद करो", "बंद करें", "रुको", "बाय")


def _load_gemini_api_key() -> str:
    key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip().strip('"').strip("'")
    if not key:
        sys.exit(1)
    return key


def _make_gemini_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def main():
    global gemini_client
    api_key = _load_gemini_api_key()
    gemini_client = _make_gemini_client(api_key)

    memory = MemoryBank.load()
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    tts_client = init_tts()

    vision = None
    if VisionSystem is not None:
        try:
            vision = VisionSystem()
            vision.start()
        except Exception:
            vision = None

    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)

    if vision:
        time.sleep(1.5)

    if vision and OWNER_NAME and vision.owner_is_present(OWNER_NAME):
        greeting = f"अरे {OWNER_NAME}, तुम्हें देखकर अच्छा लगा। कुछ बोलो।"
    elif memory.session_count > 1:
        greeting = "अरे, हम वापस आ गए — वहीं से शुरू करें जहां छोड़ा था?"
    else:
        greeting = "नमस्ते, मैं PIPPO हूं। कुछ बोलो और देखते हैं ये बातचीत कहां जाती है।"
    speak(tts_client, greeting)

    turn_counter = 0
    try:
        while True:
            try:
                user_text = listen(recognizer, mic)

                if user_text is None:
                    continue
                if user_text == "":
                    speak(tts_client, "ठीक से सुनाई नहीं दिया — फिर से बोलोगे?")
                    continue
                if user_text.strip().lower() in QUIT_WORDS:
                    speak(tts_client, "ठीक है, फिर मिलते हैं। जिज्ञासु बने रहो।")
                    break

                vision_available = vision is not None
                scene_description = vision.get_scene_description() if vision else None

                reply = generate_response(
                    memory,
                    user_text,
                    scene_description=scene_description,
                    vision_available=vision_available,
                )
                speak(tts_client, reply)

                memory.add_turn("user", user_text)
                memory.add_turn("assistant", reply)
                turn_counter += 1

                if turn_counter % FACT_UPDATE_EVERY_N_TURNS == 0:
                    update_learned_facts(memory)

                memory.save()

            except sr.WaitTimeoutError:
                continue
            except KeyboardInterrupt:
                speak(tts_client, "ठीक है, बंद कर रहा हूं।")
                break
            except Exception:
                pass
    finally:
        memory.save()
        if vision:
            vision.stop()


if __name__ == "__main__":
    main()
