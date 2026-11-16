#pragma once
#include <rex/audio/sdl/sdl_audio_driver.h>
#include <rex/audio/sdl/sdl_audio_system.h>
#include <rex/cvar.h>
#include <SDL3/SDL.h>

REXCVAR_DEFINE_STRING(audio_output_mode, "auto", "FM4/Audio", "Audio output: auto, stereo, surround")
    .allowed({"auto", "stereo", "surround"})
    .lifecycle(rex::cvar::Lifecycle::kInitOnly);

namespace fm4 {
class OutputDriver : public rex::audio::sdl::SDLAudioDriver {
 public:
  using SDLAudioDriver::SDLAudioDriver;
  bool InitializeOutput() {
#if !defined(_WIN32)
    // On Linux (PipeWire / ALSA), virtual surround endpoints report 6-8 channels
    // even for headphones/stereo speakers. Force SDL hints before Initialize() opens the stream.
    SDL_SetHint(SDL_HINT_AUDIO_CATEGORY, "playback");
    SDL_SetHint(SDL_HINT_AUDIO_CHANNELS, "2");
    SDL_SetHint(SDL_HINT_AUDIO_DEVICE_SAMPLE_FRAMES, "512");
#endif
    if (!Initialize()) return false;
    auto mode = REXCVAR_GET(audio_output_mode);
#if !defined(_WIN32)
    // Default "auto" to stereo downmix on Linux
    if (mode == "auto") {
      mode = "stereo";
    }
#else
    if (mode == "auto") return true;
#endif
    // The runtime callback folds to stereo or supplies the game's six PCM
    // channels. SDL converts to the endpoint layout configured in the OS.
    const int channels = mode == "stereo" ? 2 : 6;
    SDL_AudioSpec spec{SDL_AUDIO_F32LE, channels, 48000};
    if (!SDL_LockAudioStream(sdl_stream_)) return false;
    const bool configured = SDL_SetAudioStreamFormat(sdl_stream_, &spec, nullptr);
    if (configured) sdl_device_channels_ = static_cast<uint8_t>(channels);
    SDL_UnlockAudioStream(sdl_stream_);
    return configured;
  }
};
class OutputSystem : public rex::audio::sdl::SDLAudioSystem {
 public:
  using SDLAudioSystem::SDLAudioSystem;
  rex::X_STATUS CreateDriver(size_t, rex::thread::Semaphore* semaphore,
      rex::audio::AudioDriver** out) override {
    auto driver = std::make_unique<OutputDriver>(memory_, semaphore);
    if (!driver->InitializeOutput()) {
      driver->Shutdown();
      return static_cast<rex::X_STATUS>(0xC0000001L);
    }
    *out = driver.release();
    return 0;
  }
};
}  // namespace fm4
