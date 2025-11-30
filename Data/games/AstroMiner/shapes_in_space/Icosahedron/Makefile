# Makefile for Icosahedron Raylib Game (MinGW/GCC)

# Compiler
CXX = g++

# Directories
SRC_DIR = src
BUILD_DIR = build
BIN_DIR = bin

# Raylib paths (adjust if needed)
RAYLIB_PATH = C:/raylib
RAYLIB_INCLUDE = $(RAYLIB_PATH)/include
RAYLIB_LIB = $(RAYLIB_PATH)/lib

# Compiler flags
CXXFLAGS = -std=c++17 -Wall -Wextra -O2
INCLUDES = -I$(RAYLIB_INCLUDE)
LIBS = -L$(RAYLIB_LIB) -lraylib -lwinmm -lgdi32

# Source files
SOURCES = $(SRC_DIR)/main.cpp
OBJECTS = $(BUILD_DIR)/main.o

# Output executable
TARGET = $(BIN_DIR)/Icosahedron.exe

# Default target
all: $(TARGET)

# Create directories
$(BUILD_DIR):
	@if not exist "$(BUILD_DIR)" mkdir $(BUILD_DIR)

$(BIN_DIR):
	@if not exist "$(BIN_DIR)" mkdir $(BIN_DIR)

# Compile source files
$(BUILD_DIR)/main.o: $(SRC_DIR)/main.cpp | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c $< -o $@

# Link executable
$(TARGET): $(OBJECTS) | $(BIN_DIR)
	$(CXX) $(OBJECTS) -o $@ $(LIBS)
	@echo.
	@echo Build successful!
	@echo Executable: $(TARGET)
	@echo.
	@echo Copying raylib.dll...
	@copy "$(RAYLIB_LIB)\raylib.dll" "$(BIN_DIR)\" >nul 2>&1 || echo Warning: Could not copy raylib.dll

# Clean build files
clean:
	@if exist "$(BUILD_DIR)" rmdir /s /q $(BUILD_DIR)
	@if exist "$(BIN_DIR)" rmdir /s /q $(BIN_DIR)
	@echo Cleaned build files

# Run the game
run: $(TARGET)
	$(TARGET)

# Phony targets
.PHONY: all clean run

