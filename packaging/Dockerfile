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
      python3.12 python3.12-dev python3.12-venv \
 && rm -rf /var/lib/apt/lists/*

# Eigenes venv statt System-pip: sauber und mit Python 3.12 als "python".
RUN python3.12 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
RUN pip install --no-cache-dir --upgrade pip "pyinstaller>=6.10"
