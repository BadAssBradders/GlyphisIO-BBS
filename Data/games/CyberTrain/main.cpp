// CyberTrain unified translation unit
//
// This file intentionally stitches feature-focused .cpp modules together in the
// original order. Keeping one translation unit minimizes refactor risk while
// making future edits cheaper and more targeted.

#include "src/cybertrain_core.cpp"
#include "src/cybertrain_economy_modals.cpp"
#include "src/cybertrain_network_worldgen.cpp"
#include "src/cybertrain_exports.cpp"
#include "src/cybertrain_ui.cpp"
#include "src/cybertrain_gameloop.cpp"
#include "src/cybertrain_standalone_main.cpp"
