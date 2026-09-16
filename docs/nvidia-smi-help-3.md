Whether you’re training deep learning models, running simulations, or just curious about your GPU’s performance, **`nvidia-smi`** is your go-to command-line tool. Short for **NVIDIA System Management Interface**, this utility provides essential real-time information about your NVIDIA GPU’s health, workload, and performance.

In this blog, we’ll explore what `nvidia-smi` is, how to use it, and walk through a **real output** from a system using an **NVIDIA T1000 8GB GPU**.

### What is `nvidia-smi`?

`nvidia-smi` is a CLI utility bundled with the NVIDIA driver. It enables:

-   Real-time **GPU monitoring**
-   **Driver and CUDA version** discovery
-   Process visibility and control
-   GPU configuration and performance tuning

You can execute it using:

**nvidia-smi**

### Breakdown by Section

Let’s use real life output from a system using the T1000 8GB Nvidia GPU to review each section in detail.  

![](https://cdn.prod.website-files.com/68d15699b1e46604cd1fe6a6/68d256a8dfa02ef34b87c2a9_Screenshot-2025-08-27-at-3.42.12-PM.png)

### Driver and CUDA Info

![](https://cdn.prod.website-files.com/68d15699b1e46604cd1fe6a6/68d256a8dfa02ef34b87c2a2_Screenshot-2025-08-27-at-3.43.08-PM.png)

-   **Driver Version**: Installed NVIDIA kernel driver
-   **CUDA Version**: Max supported CUDA runtime version

### GPU Status Table

| Metric | Value |
| --- | --- |
| GPU Name | NVIDIA T1000 8GB |
| Temp | 69°C |
| Fan Speed | 52% |
| Power Cap | 50W |
| GPU Utilization | 4% |
| Memory Usage | 473 MiB / 8192 MiB |
| Performance State | P0 (max performance) |

In this case, the GPU is mostly idle, used lightly by background processes.

### Running GPU Processes  

![](https://cdn.prod.website-files.com/68d15699b1e46604cd1fe6a6/68d256a8dfa02ef34b87c2a5_Screenshot-2025-08-27-at-3.44.15-PM.png)

-   `G`: Graphics process
-   `C+G`: Uses both compute and graphics
-   `seed-version-...`: Likely a custom or sandboxed job with a version tag

To investigate it further:

```
ps -fp <span class="m">4535</span>
ls -l /proc/4535/exe
```

### Practical Use Cases

#### Monitor GPU Live

```
watch -n <span class="m">1</span> nvidia-smi
```

**Or reset the GPU:**

```
sudo nvidia-smi --gpu-reset -i <span class="m">0</span>
```

#### Query Usage via Script

```
nvidia-smi --query-gpu<span class="o">=</span>utilization.gpu,memory.used --format<span class="o">=</span>csv
```

Useful for logging and dashboards.

### Tips for Advanced Users

#### **Enable persistence mode**

```
sudo nvidia-smi -pm <span class="m">1</span>
```

#### **Restrict compute access**

```
sudo nvidia-smi -c EXCLUSIVE_PROCESS
```

#### **View app clocks**

### Summary

With tools like `nvidia-smi`, you gain critical visibility into GPU usage and health. It’s an essential part of any ML or HPC workflow. We have developed the integrated [**GPU Dashboards**](https://docs.rafay.co/dashboard/gpu_dashboard/) in the Rafay Platform to provide the same information in a graphical manner. In additionl, users do not require any form of privileged, root access to visualize this critical data.

| Feature | Benefit |
| --- | --- |
| Monitor Usage | Check GPU load, temp, memory |
| Debug Issues | Kill or trace problematic PIDs |
| Multi-GPU Support | Check all GPUs in one place |
| Script Integration | Log metrics via CSV |
| Lightweight Tool | Works even without CUDA toolkit |