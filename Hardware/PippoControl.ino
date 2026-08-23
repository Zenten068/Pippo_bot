#include <SPI.h> 
#include <Adafruit_GFX.h> 
#include <Adafruit_ST7789.h> 
#include <Arduino.h> 
#include "driver/i2s.h" 
 
 
// ===================================================== 
// ST7789 DISPLAY 
// ===================================================== 
 
#define TFT_CS   2 
#define TFT_DC   5 
#define TFT_RST  4 
 
Adafruit_ST7789 tft(TFT_CS, TFT_DC, TFT_RST); 
 
 
// ===================================================== 
// INMP441 MICROPHONE 
// ===================================================== 
 
#define I2S_PORT I2S_NUM_0 
 
#define I2S_WS   25 
#define I2S_SCK  26 
#define I2S_SD   33 
 
#define SAMPLE_RATE 16000 
#define BUFFER_SIZE 64 
 
// --- recording settings ---
#define RECORD_SECONDS        30
#define RECORD_CHUNK_SAMPLES  512   // samples per I2S read chunk while recording
 
 
// ===================================================== 
// EYE GEOMETRY 
// ===================================================== 
 
int eyeW = 60; 
int eyeMaxH = 60; 
int eyeGap = 30; 
 
int eyeCenterY; 
int leftEyeX, rightEyeX; 
 
 
uint16_t eyeColor = ST77XX_CYAN; 
uint16_t bgColor  = ST77XX_BLACK; 
 
 
// ===================================================== 
// MIC SERIAL TIMER 
// ===================================================== 
 
unsigned long lastMicPrint = 0; 

// --- emotion enum ---
enum Emotion {
  NORMAL,
  HAPPY,
  SAD,
  SURPRISED
};

// ===================================================== 
// NEW: CYCLIC EMOTION STATE 
// ===================================================== 

Emotion emotionCycle[] = { NORMAL, HAPPY, SAD, SURPRISED };
const int numEmotions = sizeof(emotionCycle) / sizeof(emotionCycle[0]);

int currentEmotionIndex = 0;
Emotion currentEmotion = NORMAL;

unsigned long lastEmotionChange = 0;
const unsigned long EMOTION_DISPLAY_MS = 2000; // how long each emotion stays on screen
 
 
// ===================================================== 
// SETUP 
// ===================================================== 
 
void setup() { 
 
  Serial.begin(115200); 
  delay(500); 
 
  Serial.println(); 
  Serial.println("=============================="); 
  Serial.println("ESP32 ROBOT"); 
  Serial.println("=============================="); 
 
 
  // =================================================== 
  // DISPLAY 
  // =================================================== 
 
  Serial.println("Initializing display..."); 
 
 
  // Hardware reset 
  pinMode(TFT_RST, OUTPUT); 
 
  digitalWrite(TFT_RST, HIGH); 
  delay(50); 
 
  digitalWrite(TFT_RST, LOW); 
  delay(50); 
 
  digitalWrite(TFT_RST, HIGH); 
  delay(150); 
 
 
  // SPI 
  SPI.begin(18, -1, 23, 5); 
 
 
  tft.init(240, 320); 
 
  tft.setRotation(3); 
 
  tft.invertDisplay(true); 
 
  tft.fillScreen(bgColor); 
 
 
  int w = tft.width(); 
  int h = tft.height(); 
 
 
  eyeCenterY = h / 2; 
 
  int totalWidth = 
    (eyeW * 2) + eyeGap; 
 
 
  leftEyeX = 
    (w - totalWidth) / 2; 
 
  rightEyeX = 
    leftEyeX + eyeW + eyeGap; 
 
 
  drawEyes(eyeMaxH); 
 
 
  Serial.println("Display OK"); 
 
 
  // =================================================== 
  // INMP441 
  // =================================================== 
 
  Serial.println("Initializing INMP441..."); 
 
 
  i2s_config_t i2s_config = { 
 
    .mode = (i2s_mode_t)( 
      I2S_MODE_MASTER | 
      I2S_MODE_RX 
    ), 
 
    .sample_rate = SAMPLE_RATE, 
 
    .bits_per_sample = 
      I2S_BITS_PER_SAMPLE_32BIT, 
 
    .channel_format = 
      I2S_CHANNEL_FMT_ONLY_LEFT, 
 
    .communication_format = 
      I2S_COMM_FORMAT_I2S, 
 
    .intr_alloc_flags = 
      ESP_INTR_FLAG_LEVEL1, 
 
    .dma_buf_count = 8, 
 
    .dma_buf_len = 
      BUFFER_SIZE, 
 
    .use_apll = false, 
 
    .tx_desc_auto_clear = false, 
 
    .fixed_mclk = 0 
  }; 
 
 
  i2s_pin_config_t pin_config = { 
 
    .bck_io_num = I2S_SCK, 
 
    .ws_io_num = I2S_WS, 
 
    .data_out_num = 
      I2S_PIN_NO_CHANGE, 
 
    .data_in_num = I2S_SD 
  }; 
 
 
  esp_err_t result; 
 
 
  result = i2s_driver_install( 
    I2S_PORT, 
    &i2s_config, 
    0, 
    NULL 
  ); 
 
 
  if (result != ESP_OK) { 
 
    Serial.print("I2S driver ERROR: "); 
    Serial.println(result); 
 
  } 
  else { 
 
    Serial.println("I2S driver OK"); 
  } 
 
 
  result = i2s_set_pin( 
    I2S_PORT, 
    &pin_config 
  ); 
 
 
  if (result != ESP_OK) { 
 
    Serial.print("I2S pin ERROR: "); 
    Serial.println(result); 
 
  } 
  else { 
 
    Serial.println("I2S pins OK"); 
  } 
 
 
  i2s_zero_dma_buffer(I2S_PORT); 
 
 
  Serial.println(); 
  Serial.println("=============================="); 
  Serial.println("MIC TEST READY"); 
  Serial.println("Speak, clap or tap near mic"); 
  Serial.println("=============================="); 


  // =================================================== 
  // RECORD 30 SECONDS OF AUDIO TO SERIAL
  // =================================================== 

  showEmotion(SURPRISED);   // "listening" face while recording
  recordAudio();            // blocks for RECORD_SECONDS, streams PCM over Serial

  Serial.println("Recording complete. Starting emotion cycle...");


  // =================================================== 
  // NEW: START THE CYCLIC EMOTION LOOP 
  // =================================================== 

  currentEmotionIndex = 0;
  currentEmotion = emotionCycle[currentEmotionIndex];
  showEmotion(currentEmotion);

  lastEmotionChange = millis();

  // stagger the blink timer so it doesn't fight the first emotion change
  // (blink only actually happens while currentEmotion == NORMAL, see loop())
} 
 
 
// ===================================================== 
// LOOP 
// ===================================================== 
 
void loop() { 
 
  // =================================================== 
  // MICROPHONE TEST 
  // =================================================== 
 
  int32_t samples[BUFFER_SIZE]; 
 
  size_t bytesRead = 0; 
 
 
  i2s_read( 
    I2S_PORT, 
    samples, 
    sizeof(samples), 
    &bytesRead, 
    10 / portTICK_PERIOD_MS 
  ); 
 
 
  if (bytesRead > 0) { 
 
    int samplesRead = 
      bytesRead / sizeof(int32_t); 
 
 
    int64_t sum = 0; 
 
 
    for (int i = 0; i < samplesRead; i++) { 
 
      // Convert INMP441 32-bit frame 
      int32_t sample = 
        samples[i] >> 14; 
 
 
      sum += abs(sample); 
    } 
 
 
    if (samplesRead > 0) { 
 
      int32_t average = 
        sum / samplesRead; 
 
 
      // Print approximately every 100 ms 
      if ( 
        millis() - lastMicPrint >= 100 
      ) { 
 
        lastMicPrint = millis(); 
 
 
        Serial.print("MIC level: "); 
        Serial.println(average); 
      } 
    } 
  } 
 
 
  // =================================================== 
  // NEW: CYCLE THROUGH EMOTIONS 
  // =================================================== 

  if (millis() - lastEmotionChange >= EMOTION_DISPLAY_MS) {

    lastEmotionChange = millis();

    currentEmotionIndex = (currentEmotionIndex + 1) % numEmotions;
    currentEmotion = emotionCycle[currentEmotionIndex];

    showEmotion(currentEmotion);
  }


  // =================================================== 
  // EYES (BLINK) — only while the face is NORMAL, 
  // so it doesn't overwrite the other emotion shapes 
  // =================================================== 
 
  static unsigned long nextBlink = 0; 
 
 
  if (currentEmotion == NORMAL && millis() >= nextBlink) { 
 
    blinkOnce(); 
 
 
    nextBlink = 
      millis() + 
      1500 + 
      random(0, 1000); 
 
 
    // Occasional double blink 
 
    if (random(0, 4) == 0) { 
 
      delay(150); 
 
      blinkOnce(); 
    } 
  } 
} 


// ===================================================== 
// RECORD AUDIO AND STREAM OVER SERIAL
// =====================================================
//
// Streams RECORD_SECONDS worth of 16-bit mono PCM samples
// (at SAMPLE_RATE) as raw bytes over Serial. A companion
// script on the PC (save_audio.py) listens for the
// "AUDIO_RECORD_START" line, then reads exactly
// SAMPLE_RATE * RECORD_SECONDS * 2 bytes and writes them
// to a .wav file.

void recordAudio() {

  Serial.println("AUDIO_RECORD_START");
  delay(50); // give the marker line time to flush before binary data starts

  int32_t rawBuffer[RECORD_CHUNK_SAMPLES];
  int16_t outBuffer[RECORD_CHUNK_SAMPLES];

  unsigned long totalSamples = (unsigned long)SAMPLE_RATE * RECORD_SECONDS;
  unsigned long samplesSent = 0;

  while (samplesSent < totalSamples) {

    size_t bytesRead = 0;

    i2s_read(
      I2S_PORT,
      rawBuffer,
      sizeof(rawBuffer),
      &bytesRead,
      portMAX_DELAY
    );

    int samplesInChunk = bytesRead / sizeof(int32_t);

    // Don't overshoot the requested total sample count
    if (samplesSent + samplesInChunk > totalSamples) {
      samplesInChunk = totalSamples - samplesSent;
    }

    for (int i = 0; i < samplesInChunk; i++) {

      int32_t sample = rawBuffer[i] >> 14;

      if (sample > 32767)  sample = 32767;
      if (sample < -32768) sample = -32768;

      outBuffer[i] = (int16_t)sample;
    }

    Serial.write((uint8_t*)outBuffer, samplesInChunk * sizeof(int16_t));

    samplesSent += samplesInChunk;
  }

  Serial.println();
  Serial.println("AUDIO_RECORD_END");
}
 
 
// ===================================================== 
// DRAW EYES (NORMAL / IDLE / BLINK ANIMATION) 
// ===================================================== 
 
void drawEyes(int h) { 
 
  int leftEyeY = 
    eyeCenterY - h / 2; 
 
  int rightEyeY = 
    eyeCenterY - h / 2; 
 
 
  // Clear full eye area 
 
  tft.fillRect( 
    leftEyeX, 
    eyeCenterY - eyeMaxH / 2, 
    eyeW, 
    eyeMaxH, 
    bgColor 
  ); 
 
 
  tft.fillRect( 
    rightEyeX, 
    eyeCenterY - eyeMaxH / 2, 
    eyeW, 
    eyeMaxH, 
    bgColor 
  ); 
 
 
  // Draw eyes 
 
  if (h > 0) { 
 
    tft.fillRect( 
      leftEyeX, 
      leftEyeY, 
      eyeW, 
      h, 
      eyeColor 
    ); 
 
 
    tft.fillRect( 
      rightEyeX, 
      rightEyeY, 
      eyeW, 
      h, 
      eyeColor 
    ); 
  } 
} 
 
 
// ===================================================== 
// BLINK 
// ===================================================== 
 
void blinkOnce() { 
 
  // Close 
 
  for ( 
    int h = eyeMaxH; 
    h >= 0; 
    h -= 6 
  ) { 
 
    drawEyes(h); 
 
    delay(12); 
  } 
 
 
  drawEyes(0); 
 
  delay(60); 
 
 
  // Open 
 
  for ( 
    int h = 0; 
    h <= eyeMaxH; 
    h += 6 
  ) { 
 
    drawEyes(h); 
 
    delay(12); 
  } 
 
 
  // Restore the proper NORMAL shape (rounded rect) rather than 
  // the plain rectangle used mid-animation 
  showEmotion(NORMAL);
}


// ===================================================== 
// EMOTIONS
// =====================================================

void clearEyeArea() {

  int margin = 20; // extra room for the bigger "surprised" circles

  tft.fillRect(
    leftEyeX - margin,
    eyeCenterY - eyeMaxH / 2 - margin,
    eyeW + margin * 2,
    eyeMaxH + margin * 2,
    bgColor
  );

  tft.fillRect(
    rightEyeX - margin,
    eyeCenterY - eyeMaxH / 2 - margin,
    eyeW + margin * 2,
    eyeMaxH + margin * 2,
    bgColor
  );
}

void showEmotion(Emotion e) {

  clearEyeArea();

  switch (e) {

    case NORMAL: {
      tft.fillRoundRect(
        leftEyeX, eyeCenterY - eyeMaxH / 2,
        eyeW, eyeMaxH, 8, eyeColor
      );
      tft.fillRoundRect(
        rightEyeX, eyeCenterY - eyeMaxH / 2,
        eyeW, eyeMaxH, 8, eyeColor
      );
      break;
    }

    case HAPPY: {
      // upward "^" curves, like squinting/smiling eyes
      int topY = eyeCenterY - eyeMaxH / 2;
      int midY = eyeCenterY + eyeMaxH / 4;

      tft.fillTriangle(
        leftEyeX, midY,
        leftEyeX + eyeW / 2, topY,
        leftEyeX + eyeW, midY,
        eyeColor
      );

      tft.fillTriangle(
        rightEyeX, midY,
        rightEyeX + eyeW / 2, topY,
        rightEyeX + eyeW, midY,
        eyeColor
      );
      break;
    }

    case SAD: {
      // drooping outer corners, higher inner corners
      int topOuter  = eyeCenterY - eyeMaxH / 4;
      int topInner  = eyeCenterY - eyeMaxH / 2;
      int bottomY   = eyeCenterY + eyeMaxH / 2;

      // left eye (droops toward the outside/left)
      tft.fillTriangle(
        leftEyeX, topOuter,
        leftEyeX + eyeW, topInner,
        leftEyeX + eyeW, bottomY,
        eyeColor
      );
      tft.fillTriangle(
        leftEyeX, topOuter,
        leftEyeX, bottomY,
        leftEyeX + eyeW, bottomY,
        eyeColor
      );

      // right eye (mirrored, droops toward the outside/right)
      tft.fillTriangle(
        rightEyeX + eyeW, topOuter,
        rightEyeX, topInner,
        rightEyeX, bottomY,
        eyeColor
      );
      tft.fillTriangle(
        rightEyeX + eyeW, topOuter,
        rightEyeX + eyeW, bottomY,
        rightEyeX, bottomY,
        eyeColor
      );
      break;
    }

    case SURPRISED: {
      int r = eyeMaxH / 2 + 10;

      tft.fillCircle(leftEyeX + eyeW / 2, eyeCenterY, r, eyeColor);
      tft.fillCircle(rightEyeX + eyeW / 2, eyeCenterY, r, eyeColor);
      break;
    }
  }
}
