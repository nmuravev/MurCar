# 🖥️ Настройка Orange Pi 5

## Требования к оборудованию

### Минимальные требования
- **Плата**: Orange Pi 5 LTS (или Orange Pi 5/5B/5 Plus)
- **Процессор**: RK3588S (8 ядер: 4x Cortex-A76 + 4x Cortex-A55)
- **NPU**: 6 TOPS (для ускорения нейросети)
- **ОЗУ**: Минимум 8GB (рекомендуется 16GB или 32GB)
- **Накопитель**: microSD карта 64GB+ или eMMC 32GB+ (рекомендуется SSD NVMe)
- **Питание**: USB-C PD 5V/4A или DC 12V/2A

### Рекомендуемая конфигурация
- **Orange Pi 5 LTS** с 16GB RAM
- **SSD NVMe 128GB+** (через M.2 слот) для лучшей производительности
- **Активное охлаждение** (вентилятор + радиатор)
- **Корпус** с вентиляцией
- **USB Hub с внешним питанием** (для 5 USB камер)

## Установка операционной системы

### Вариант 1: Orange Pi OS (Droid)
Рекомендуется для максимальной совместимости с железом.

1. Скачайте образ с [официального сайта](https://www.orangepi.org/)
2. Запишите образ на microSD карту или eMMC:
   ```bash
   sudo dd if=orangepi-os.img of=/dev/sdX bs=4M status=progress
   ```
3. Вставьте карту в плату и включите питание
4. Первоначальная настройка через HDMI или SSH

### Вариант 2: Ubuntu 22.04 LTS (Armbian)
Альтернатива с большим сообществом.

1. Скачайте Armbian для Orange Pi 5
2. Запишите образ аналогично выше
3. Первый вход:
   - Логин: `root`
   - Пароль: `1234` (смените при первом входе)

### Вариант 3: Debian Bookworm
Стабильная версия с долгосрочной поддержкой.

## Первоначальная настройка системы

### 1. Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### 2. Настройка локали и времени
```bash
sudo timedatectl set-timezone Europe/Moscow
sudo localectl set-locale LANG=ru_RU.UTF-8
sudo reboot
```

### 3. Создание пользователя
```bash
sudo adduser droneops
sudo usermod -aG sudo droneops
sudo usermod -aG video droneops
```

### 4. Настройка SSH
```bash
sudo systemctl enable ssh
sudo systemctl start ssh

# Редактирование конфига
sudo nano /etc/ssh/sshd_config
# Измените:
# PermitRootLogin no
# PasswordAuthentication no
# PubkeyAuthentication yes

sudo systemctl restart ssh
```

### 5. Настройка сети

#### Статический IP (Ethernet)
```bash
sudo nano /etc/netplan/01-netcfg.yaml
```

```yaml
network:
  version: 2
  ethernets:
    eth0:
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 1.1.1.1
```

Применение:
```bash
sudo netplan apply
```

#### Настройка Wi-Fi (если используется)
```bash
sudo nmcli device wifi connect "SSID" password "PASSWORD"
```

### 6. Установка необходимых пакетов
```bash
sudo apt install -y \
    git \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    cmake \
    build-essential \
    libusb-1.0-0-dev \
    libgtk-3-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    gfortran \
    openexr \
    libatlas-base-dev \
    wget \
    curl \
    htop \
    i2c-tools \
    lm-sensors
```

## Настройка NPU (Rockchip NPU)

### 1. Установка драйверов NPU
```bash
# Проверка наличия NPU
lsusb | grep Rockchip

# Установка rknn-toolkit2
cd ~
git clone https://github.com/airockchip/rknn-toolkit2.git
cd rknn-toolkit2

# Установка Python зависимостей
cd runtime/python3
python3 -m pip install rknn_toolkit2-*.whl
```

### 2. Проверка работы NPU
```bash
python3 -c "from rknn.api import RKNN; print('NPU OK')"
```

### 3. Настройка прав доступа
```bash
sudo usermod -aG render droneops
sudo chmod 666 /dev/rknpu
```

Для постоянного применения:
```bash
sudo nano /etc/udev/rules.d/99-rockchip-npu.rules
```
Добавьте:
```
SUBSYSTEM=="rknpu", MODE="0666"
```

## Настройка USB для камер

### 1. Проверка USB контроллеров
```bash
lsusb -t
```

Ожидаемая структура для Orange Pi 5:
```
/:  Bus 04.Port 1: Dev 1, Class=root_hub, Driver=xhci-hcd/1p, 10000M
/:  Bus 03.Port 1: Dev 1, Class=root_hub, Driver=xhci-hcd/1p, 480M
/:  Bus 02.Port 1: Dev 1, Class=root_hub, Driver=xhci-hcd/4p, 10000M
    |__ Port 1: Dev 2, If 0, Class=Video, Driver=uvcvideo, 5000M
    |__ Port 2: Dev 3, If 0, Class=Video, Driver=uvcvideo, 5000M
    ...
/:  Bus 01.Port 1: Dev 1, Class=root_hub, Driver=xhci-hcd/1p, 480M
```

### 2. Увеличение лимита USB bandwidth
```bash
sudo nano /etc/modprobe.d/usb.conf
```
Добавьте:
```
options usbcore autosuspend=-1
options uvcvideo nodrop=1 timeout=5000 quirks=0x80:0x0
```

### 3. Применение изменений
```bash
sudo update-initramfs -u
sudo reboot
```

### 4. Проверка пропускной способности
```bash
# Для каждой камеры проверьте:
cat /sys/kernel/debug/usb/devices | grep -A 20 "Bus.*Dev"
```

## Мониторинг системы

### 1. Установка инструментов мониторинга
```bash
sudo apt install -y \
    htop \
    iotop \
    nethogs \
    glances
```

### 2. Мониторинг температуры
```bash
watch -n 1 cat /sys/class/thermal/thermal_zone*/temp
```

### 3. Мониторинг NPU
```bash
sudo cat /sys/class/devfreq/fdabf000.npu/load
```

### 4. Скрипт мониторинга
Создайте файл `/usr/local/bin/op5-monitor.sh`:
```bash
#!/bin/bash
echo "=== Orange Pi 5 Monitor ==="
echo "CPU Temp: $(cat /sys/class/thermal/thermal_zone0/temp)°C"
echo "CPU Load: $(top -bn1 | grep 'Cpu(s)' | awk '{print $2}')%"
echo "Memory: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "NPU Load: $(cat /sys/class/devfreq/fdabf000.npu/load 2>/dev/null || echo 'N/A')%"
echo "Uptime: $(uptime -p)"
echo ""
echo "USB Devices:"
lsusb | grep -E "Camera|Imaging"
echo ""
echo "Network:"
ip -br addr show | grep -v "lo"
```

Сделайте исполняемым:
```bash
sudo chmod +x /usr/local/bin/op5-monitor.sh
```

## Оптимизация производительности

### 1. Разгон (опционально, на свой страх и риск)
```bash
sudo nano /boot/armbianEnv.txt
```
Добавьте:
```
overclock_cpu=2256
overclock_gpu=1000
overclock_npu=1000
```

### 2. Настройка swap (для 8GB RAM)
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Постоянное включение
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 3. Отключение ненужных сервисов
```bash
sudo systemctl disable bluetooth
sudo systemctl disable cups
sudo systemctl disable avahi-daemon
```

## Резервное копирование

### Создание бэкапа системы
```bash
sudo dd if=/dev/mmcblk0 of=~/orangepi-backup.img bs=4M status=progress
```

### Восстановление из бэкапа
```bash
sudo dd if=orangepi-backup.img of=/dev/mmcblk0 bs=4M status=progress
```

## Решение проблем

### Камеры не определяются
```bash
# Проверка питания USB
lsusb -v | grep -i "maxpower"

# Перезагрузка USB контроллера
sudo modprobe -r uvcvideo
sudo modprobe uvcvideo
```

### NPU не работает
```bash
# Проверка драйверов
dmesg | grep -i rockchip

# Перезагрузка службы
sudo systemctl restart rockchip-npu
```

### Перегрев
- Установите активное охлаждение
- Снизьте частоты CPU/NPU
- Проверьте термопасту

## Следующие шаги

После настройки Orange Pi перейдите к:
- [Настройке камер](camera_configuration.md)
- [Установке ПО](../../deployment/installation.md)
- [Конфигурации сети](network_setup.md)
