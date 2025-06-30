#!/bin/bash

ZIP_SOURCE="/home/USUARIO/tailscale_install/tailscale_1.84.0_arm.tgz"
BACKUP_DIR="/opt/tailscale_backup"
EXTRACT_DIR="$BACKUP_DIR/tailscale_1.84.0_arm"
INSTALL_DIR="/usr/local/bin"

mkdir -p "$BACKUP_DIR"
rm -rf "$EXTRACT_DIR"

# Extrai o arquivo tgz
cp "$ZIP_SOURCE" "$BACKUP_DIR/"
tar -xzf "$BACKUP_DIR/tailscale_1.84.0_arm.tgz" -C "$BACKUP_DIR/"

# Restaura binários
cp "$EXTRACT_DIR/tailscale" "$INSTALL_DIR/"
cp "$EXTRACT_DIR/tailscaled" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/tailscale" "$INSTALL_DIR/tailscaled"

# Validação
if file "$INSTALL_DIR/tailscale" | grep -q 'ELF' && file "$INSTALL_DIR/tailscaled" | grep -q 'ELF'; then
  echo "[INFO] Tailscale restaurado com sucesso."
  rm -f "$BACKUP_DIR/tailscale_1.84.0_arm.tgz"
  rm -rf "$EXTRACT_DIR"
else
  echo "[ERRO] Falha na restauração dos binários."
fi
