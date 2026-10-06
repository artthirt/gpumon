[Alireza Olama](https://fi.linkedin.com/in/alireza-olama-213a6a107) ![Alireza Olama](https://static.licdn.com/aero-v1/sc/h/9c8pery4andzj6ohjkjp54ma2)

### Alireza Olama

Опубликовано 2 янв. 2025 г.

GPU monitoring is crucial in high-performance computing (HPC) applications to ensure optimal performance, efficient resource utilization, and system stability. By tracking metrics such as memory usage, temperature, and processing load, developers can identify bottlenecks, prevent overheating, and optimize their code for maximum efficiency. In this tutorial, I explain how to query various useful information about #NVIDIA GPUs by using the NVML library.

___

### What is NVML?

NVML is a low-level API provided by NVIDIA to help developers interact with and manage GPU hardware. It comes bundled with NVIDIA CUDA Toolkit and supports most modern NVIDIA GPUs.

NVML allows for real-time monitoring of GPU memory usage and provides insights into the GPU's performance by tracking utilization, temperature, and power consumption. Additionally, NVML enables monitoring of processes running on the GPU and helps with error management by querying ECC errors and other GPU-related events. It also provides control over power limits and thermal thresholds to optimize GPU performance and ensure proper functioning.

> Before you can use NVML, there are a few prerequisites to consider. First, make sure that the NVIDIA drivers and CUDA Toolkit are installed on your system. The NVML header and library are also required, and these are typically included when you install the CUDA Toolkit. The header file is named ''nvml.h'', while the library file is either ''nvml.lib'' on Windows or ''libnvidia-ml.so'' on Linux.

___

### Getting Started

To use NVML in a C++ project, include the header and link the library:

The workflow for using NVML generally follows these steps:

1\. Initialize NVML

```
nvmlReturn_t result = nvmlInit();
if (result != NVML_SUCCESS) {
    std::cerr << "Failed to initialize NVML: " << nvmlErrorString(result) << std::endl;
    return -1;
}        
```

2\. Get Device Count

```
unsigned int deviceCount;
result = nvmlDeviceGetCount(&deviceCount);
if (result != NVML_SUCCESS) {
    std::cerr << "Failed to query device count: " << nvmlErrorString(result) << std::endl;
    nvmlShutdown();
    return -1;
}        
```

3\. Query GPU Information

## Рекомендовано компанией LinkedIn

```
for (unsigned int i = 0; i < deviceCount; ++i) {
    nvmlDevice_t device;
    result = nvmlDeviceGetHandleByIndex(i, &device);
    if (result != NVML_SUCCESS) {
        std::cerr << "Failed to get handle for device " << i << ": " << nvmlErrorString(result) << std::endl;
        continue;
    }

    char name[NVML_DEVICE_NAME_BUFFER_SIZE];
    result = nvmlDeviceGetName(device, name, NVML_DEVICE_NAME_BUFFER_SIZE);
    if (result == NVML_SUCCESS) {
        std::cout << "Device " << i << ": " << name << std::endl;
    }
}        
```

4\. Query Memory Usage

```
nvmlMemory_t memory;
result = nvmlDeviceGetMemoryInfo(device, &memory);
if (result == NVML_SUCCESS) {
    std::cout << "  Total Memory: " << memory.total / (1024 * 1024) << " MB\n";
    std::cout << "  Used Memory:  " << memory.used / (1024 * 1024) << " MB\n";
    std::cout << "  Free Memory:  " << memory.free / (1024 * 1024) << " MB\n";
}        
```

5\. Shutdown NVML

___

### Examples

Example 1:

This program monitors all GPUs on the system and displays their memory usage and utilization

```
#include <iostream>
#include <nvml.h>

int main() {
    nvmlReturn_t result = nvmlInit();
    if (result != NVML_SUCCESS) {
        std::cerr << "Failed to initialize NVML: " << nvmlErrorString(result) << std::endl;
        return -1;
    }

    unsigned int deviceCount;
    nvmlDeviceGetCount(&deviceCount);

    for (unsigned int i = 0; i < deviceCount; ++i) {
        nvmlDevice_t device;
        nvmlDeviceGetHandleByIndex(i, &device);

        char name[NVML_DEVICE_NAME_BUFFER_SIZE];
        nvmlDeviceGetName(device, name, NVML_DEVICE_NAME_BUFFER_SIZE);
        std::cout << "Device " << i << ": " << name << std::endl;

        nvmlMemory_t memory;
        nvmlDeviceGetMemoryInfo(device, &memory);
        std::cout << "  Total Memory: " << memory.total / (1024 * 1024) << " MB\n";
        std::cout << "  Used Memory:  " << memory.used / (1024 * 1024) << " MB\n";
        std::cout << "  Free Memory:  " << memory.free / (1024 * 1024) << " MB\n";

        nvmlUtilization_t utilization;
        nvmlDeviceGetUtilizationRates(device, &utilization);
        std::cout << "  GPU Utilization: " << utilization.gpu << "%\n";
        std::cout << "  Memory Utilization: " << utilization.memory << "%\n";
    }

    nvmlShutdown();
    return 0;
}        
```

Example 2:

This code checks if any GPU exceeds a specified temperature threshold:

```
#include <iostream>
#include <nvml.h>

int main() {
    const int TEMP_THRESHOLD = 85; // in degrees Celsius

    nvmlInit();
    unsigned int deviceCount;
    nvmlDeviceGetCount(&deviceCount);

    for (unsigned int i = 0; i < deviceCount; ++i) {
        nvmlDevice_t device;
        nvmlDeviceGetHandleByIndex(i, &device);

        unsigned int temp;
        nvmlDeviceGetTemperature(device, NVML_TEMPERATURE_GPU, &temp);

        if (temp > TEMP_THRESHOLD) {
            char name[NVML_DEVICE_NAME_BUFFER_SIZE];
            nvmlDeviceGetName(device, name, NVML_DEVICE_NAME_BUFFER_SIZE);
            std::cerr << "Warning: " << name << " exceeds temperature threshold (" << temp << " °C)\n";
        }
    }

    nvmlShutdown();
    return 0;
}        
```

___

### Conclusion

NVML is an essential tool for developers and system administrators who work with NVIDIA GPUs. It provides robust functionality for monitoring and managing GPUs in various environments, from personal systems to large-scale data centers. By following the examples and workflow in this tutorial, you can leverage NVML to build powerful GPU-aware applications.

For detailed documentation, refer to the [official NVIDIA NVML Developer Guide.](https://docs.nvidia.com/deploy/nvml-api/index.html)

 [![](https://static.licdn.com/aero-v1/sc/h/bn39hirwzjqj18ej1fkz55671) ![](https://static.licdn.com/aero-v1/sc/h/2tzoeodxy0zug4455msr0oq0v)](https://www.linkedin.com/signup/cold-join?session_redirect=%2Fpulse%2Fshort-tutorial-nvidia-management-library-nvml-alireza-olama-8ld6f&trk=article-ssr-frontend-pulse_x-social-details_likes-count_social-actions-reactions)

## Другие статьи участника Alireza Olama

## Другие участники также просматривали

## Похожие темы

## Просмотр категорий контента