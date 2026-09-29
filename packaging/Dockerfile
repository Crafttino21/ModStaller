# Baut Backend und zsign auf Ubuntu 22.04 (glibc 2.35).
#
# Warum so alt: ein Binary laeuft nur auf Systemen mit mindestens der glibc,
# gegen die es gebaut wurde. Auf Arch gebaut, startete die AppImage z. B. auf
# Ubuntu 22.04 nicht. glibc 2.35 deckt Ubuntu 22.04+, Debian 12+, aktuelle
# Fedora und Arch ab.
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends software-properties-common gpg-agent \
 && add-apt-repository -y ppa:deadsnakes/ppa \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential pkg-config git ca-certificates libssl-dev binutils \
      python3.13 python3.13-dev python3.13-venv \
 && rm -rf /var/lib/apt/lists/*

# Eigenes venv statt System-pip: sauber und mit Python 3.13 als "python".
#
# Mindestens 3.13: erst ab da kann Pythons eigenes ssl TLS-PSK
# (set_psk_client_callback), das der Netzwerk-Tunnel zu iPhone, Apple TV
# und Vision Pro braucht. Darunter nimmt pymobiledevice3 sslpsk_pmd3 - dessen
# Wheel bringt ein eigenes OpenSSL 1.0.2 mit, das sich mit dem von Python
# nicht versteht: "NO_CIPHERS_AVAILABLE", der Tunnel steht nie.
RUN python3.13 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
RUN pip install --no-cache-dir --upgrade pip "pyinstaller>=6.10"
