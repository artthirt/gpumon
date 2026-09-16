# NVIDIA-SMI Comprehensive Cheat Sheet

## Overview

`nvidia-smi` (NVIDIA System Management Interface) is a command-line tool that provides monitoring, management, and diagnostic information for NVIDIA GPU devices.

It communicates directly with the NVIDIA driver and GPU, and can:
- Monitor GPU performance, temperature, and utilization
- Manage power, clock speeds, and ECC
- Control persistence mode and compute modes
- Query detailed metrics for automation and monitoring

---

## Basic Usage

```bash
nvidia-smi
```

Shows a summary table with:
- GPU index, name, and UUID  
- Driver & CUDA versions  
- GPU & memory utilization  
- Power consumption and temperature  
- Active processes using the GPU  

---

## General Commands

| Command | Description |
|----------|--------------|
| `nvidia-smi -h` | Show help and usage information |
| `nvidia-smi --version` | Display the version of `nvidia-smi` |
| `nvidia-smi -L` | List all GPUs with their UUIDs |
| `nvidia-smi -q` | Display detailed information for all GPUs |
| `nvidia-smi -i <index> -q` | Display details for a specific GPU |
| `nvidia-smi -q -d <category>` | Display a specific data category (e.g. TEMPERATURE, PERFORMANCE) |
| `nvidia-smi -x -q` | Output detailed info in XML format |
| `nvidia-smi topo -m` | Display topology matrix between GPUs (PCIe/NVLink) |

---

## Continuous Monitoring

### Looping Output
```bash
nvidia-smi -l 5
```

### Millisecond Interval
```bash
nvidia-smi -lms 500
```

### Log to File
```bash
nvidia-smi --filename=/var/log/gpu.log -l 5
```

---

## Dynamic Monitoring

```bash
nvidia-smi dmon
```

Example:
```
# gpu   pwr  temp   sm   mem  enc  dec  mclk  pclk
    0    85    64   23     5    0    0  405  1110
```

---

## Querying GPU Information

```bash
nvidia-smi --query-gpu=index,name,uuid,temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv
```

Output:
```
index, name, uuid, temperature.gpu, utilization.gpu [%], memory.used [MiB], memory.total [MiB]
0, NVIDIA RTX A6000, GPU-02afcc1a-…, 58, 72 %, 13456 MiB, 49152 MiB
```

### Common Query Fields
| Category | Example Fields |
|-----------|----------------|
| **Identity** | `index`, `name`, `uuid`, `serial`, `vbios_version` |
| **Performance** | `utilization.gpu`, `utilization.memory`, `pstate`, `clocks.current.graphics` |
| **Memory** | `memory.total`, `memory.used`, `memory.free` |
| **Temperature** | `temperature.gpu`, `temperature.memory` |
| **Power** | `power.draw`, `power.limit`, `power.default_limit` |
| **Fan/Clocks** | `fan.speed`, `clocks.gr`, `clocks.mem`, `clocks.video` |
| **Driver** | `driver_version`, `cuda_version` |

---

## Examples

### Show GPU Memory Usage
```bash
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

### Show GPU Temperature and Power Draw
```bash
nvidia-smi --query-gpu=temperature.gpu,power.draw --format=csv,noheader,nounits
```

### List All GPU Names
```bash
nvidia-smi --query-gpu=name --format=csv,noheader
```

### Show Active Compute Processes
```bash
nvidia-smi pmon -c 1
```

---

## Process Monitoring

```bash
nvidia-smi pmon
```

Example output:
```
# gpu   pid  type   sm   mem   enc   dec   command
    0  3024     C    23     5     0     0   python3
```

Terminate a process:
```bash
sudo kill -9 <pid>
```

---

## Configuration and Management

### Enable Persistence Mode
```bash
sudo nvidia-smi -pm 1
```

### Disable Persistence Mode
```bash
sudo nvidia-smi -pm 0
```

### Change Power Limit
```bash
sudo nvidia-smi -pl 250
```

### Lock GPU Clocks
```bash
sudo nvidia-smi --lock-gpu-clocks=900,1500
```

### Unlock GPU Clocks
```bash
sudo nvidia-smi --reset-gpu-clocks
```

### Lock Memory Clocks
```bash
sudo nvidia-smi --lock-memory-clocks=405,1215
```

### Reset a GPU
```bash
sudo nvidia-smi -i 0 --gpu-reset
```

---

## Compute & ECC Configuration

### Show ECC Status
```bash
nvidia-smi -q -d ECC
```

### Enable ECC
```bash
sudo nvidia-smi -e 1
```

### Set Compute Mode
| Mode | Description |
|------|--------------|
| `0` | Default (Multiple contexts allowed) |
| `1` | Exclusive thread |
| `2` | Prohibited |
| `3` | Exclusive process |

Example:
```bash
sudo nvidia-smi -c 3
```

---

## Diagnostic and System Info

### Show Supported Clocks
```bash
nvidia-smi -q -d SUPPORTED_CLOCKS
```

### Show Performance State
```bash
nvidia-smi -q -d PERFORMANCE
```

### Show PCIe Info
```bash
nvidia-smi -q -d PCI
```

### Show Fan Info
```bash
nvidia-smi -q -d FAN
```

---

## Advanced Output Control

### CSV Output without Headers
```bash
nvidia-smi --query-gpu=name,utilization.gpu --format=csv,noheader
```

### CSV without Units
```bash
nvidia-smi --query-gpu=temperature.gpu --format=csv,nounits
```

### Save to File
```bash
nvidia-smi --query-gpu=index,uuid,temperature.gpu,power.draw --format=csv -l 10 --filename=gpu_stats.csv
```

---

## Automation Tips

- Use `--query-gpu` with `--format=csv,noheader,nounits` in scripts.
- Use GPU UUIDs for consistent identification.
- Combine with `watch`:
  ```bash
  watch -n 2 nvidia-smi
  ```

---

## Example Monitoring Script

```bash
#!/bin/bash
LOGFILE="/var/log/nvidia_smi_monitor.csv"

echo "timestamp,gpu_index,uuid,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw" > $LOGFILE

while true; do
  nvidia-smi --query-gpu=timestamp,index,uuid,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw              --format=csv,noheader >> $LOGFILE
  sleep 5
done
```

---

## Common Issues

| Issue | Solution |
|--------|-----------|
| `NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver` | Ensure driver is loaded or reinstall driver. |
| `Insufficient permissions` | Add `sudo` for management commands. |
| `GPU Reset not supported` | Some models don’t allow GPU reset. |
| `Compute mode changes not persisting` | Reboot after applying. |

---
