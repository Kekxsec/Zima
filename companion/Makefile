BINARY    := zima-companion
DIST_DIR  := dist

.PHONY: build-mac-arm build-mac-x86 build-mac build-linux build-windows build-all test lint clean

build-mac-arm:
	cargo build --release --target aarch64-apple-darwin
	mkdir -p $(DIST_DIR)
	cp target/aarch64-apple-darwin/release/$(BINARY) $(DIST_DIR)/$(BINARY)-arm64

build-mac-x86:
	cargo build --release --target x86_64-apple-darwin
	mkdir -p $(DIST_DIR)
	cp target/x86_64-apple-darwin/release/$(BINARY) $(DIST_DIR)/$(BINARY)-x86_64

build-mac: build-mac-arm build-mac-x86
	lipo -create -output $(DIST_DIR)/$(BINARY)-macos \
		$(DIST_DIR)/$(BINARY)-arm64 \
		$(DIST_DIR)/$(BINARY)-x86_64
	@echo "Universal macOS binary: $(DIST_DIR)/$(BINARY)-macos"

build-linux:
	cargo build --release --target x86_64-unknown-linux-gnu
	mkdir -p $(DIST_DIR)
	cp target/x86_64-unknown-linux-gnu/release/$(BINARY) $(DIST_DIR)/$(BINARY)-linux-x86_64

build-windows:
	cargo build --release --target x86_64-pc-windows-gnu
	mkdir -p $(DIST_DIR)
	cp target/x86_64-pc-windows-gnu/release/$(BINARY).exe $(DIST_DIR)/$(BINARY)-windows-x86_64.exe

build-all: build-mac build-linux build-windows

test:
	cargo test

lint:
	cargo fmt --check
	cargo clippy -- -D warnings

clean:
	cargo clean
	rm -rf $(DIST_DIR)
