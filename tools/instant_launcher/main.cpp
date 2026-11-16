// Forza Motorsport 4 - Instant Game Launcher
// Launches the game directly with the active profile and saved settings.

#include <unistd.h>
#include <cstdlib>
#include <filesystem>
#include <string>
#include <vector>

namespace fs = std::filesystem;

int main(int argc, char** argv) {
  fs::path self;
  std::error_code ec;
  self = fs::canonical("/proc/self/exe", ec);
  if (ec || self.empty()) {
    self = fs::current_path() / argv[0];
  }
  fs::path dir = self.parent_path();
  fs::path launcher = dir / "fm4-launcher";
  if (!fs::exists(launcher)) {
    if (fs::exists(fs::current_path() / "fm4-launcher")) {
      launcher = fs::current_path() / "fm4-launcher";
      dir = fs::current_path();
    }
  }

  // Ensure working directory is set to the installation folder
  chdir(dir.c_str());

  std::vector<std::string> args_storage;
  args_storage.push_back(launcher.u8string());
  args_storage.push_back("--play");
  for (int i = 1; i < argc; ++i) {
    args_storage.push_back(argv[i]);
  }

  std::vector<char*> args;
  for (auto& s : args_storage) {
    args.push_back(s.data());
  }
  args.push_back(nullptr);

  execv(launcher.c_str(), args.data());
  return 1;
}
