[Перейти к содержимому](moz-extension://4cbd161a-1e71-4457-871a-de8598dbfbce/_generated_background_page.html#wp--skip-link--target)

## Мониторинг и управление GPU NVIDIA через nvidia-smi

![](https://krivoshein.site/wp-content/uploads/2025/02/dall-e-2025-02-09-14.33.19-a-futuristic-server-room-filled-with-multiple-nvidia-gpus-with-a-terminal-screen-displaying-nvidia-smi-output-in-green-text.-the-environment-is-dim.webp)

Оглавление9

1.  [Базовая сводка по GPU](moz-extension://4cbd161a-1e71-4457-871a-de8598dbfbce/_generated_background_page.html#bazovaya-svodka-po-gpu)
2.  [Версия драйвера и CUDA](moz-extension://4cbd161a-1e71-4457-871a-de8598dbfbce/_generated_background_page.html#versiya-drayvera-i-cuda)
3.  [Энергопотребление и power limit](moz-extension://4cbd161a-1e71-4457-871a-de8598dbfbce/_generated_background_page.html#energopotreblenie-i-power-limit)
4.  [Процессы на GPU](moz-extension://4cbd161a-1e71-4457-871a-de8598dbfbce/_generated_background_page.html#protsessy-na-gpu)
5.  [Логирование](moz-extension://4cbd161a-1e71-4457-871a-de8598dbfbce/_generated_background_page.html#logirovanie)
6.  [Полезные query-поля](moz-extension://4cbd161a-1e71-4457-871a-de8598dbfbce/_generated_background_page.html#poleznye-query-polya)
7.  [На что смотреть на практике](moz-extension://4cbd161a-1e71-4457-871a-de8598dbfbce/_generated_background_page.html#na-chto-smotret-na-praktike)
8.  [Итог](moz-extension://4cbd161a-1e71-4457-871a-de8598dbfbce/_generated_background_page.html#itog)
9.  [Источники и ссылки](moz-extension://4cbd161a-1e71-4457-871a-de8598dbfbce/_generated_background_page.html#istochniki-i-ssylki)

**nvidia-smi** (NVIDIA System Management Interface) – штатная CLI для мониторинга и частичного управления GPU NVIDIA. Идёт вместе с драйвером, отдельный «тяжёлый» стек не нужен. Ниже – базовая сводка, query/format, power limit, процессы и простое логирование.

## Базовая сводка по GPU

Команда без аргументов показывает таблицу по всем видимым картам:

```
nvidia-smi
```

В шапке обычно видны версия драйвера и заявленная поддержка CUDA. В таблице по GPU:

-   имя модели, bus-id, persistence mode;
-   вентилятор, температура, perf state, power draw / power cap;
-   занятая / суммарная видеопамять;
-   GPU-Util, compute mode;
-   ниже – процессы, которые держат контекст на GPU (PID, тип, память).

Условный фрагмент вывода (цифры и модель зависят от железа):

+-----------------------------------------------------------------------------+

| NVIDIA-SMI 535.104.05 Driver Version: 535.104.05 CUDA Version: 12.2 |

|-------------------------------+----------------------+----------------------+

| GPU Name Persistence-M| Bus-Id Disp.A | Volatile Uncorr. ECC |

| Fan Temp Perf Pwr:Usage/Cap| Memory-Usage | GPU-Util Compute M. |

| 0 NVIDIA RTX 4090 On | 00000000:01:00.0 Off | Off |

| 34% 65C P8 15W / 450W | 4000MiB / 24576MiB | 12% Default |

+-------------------------------+----------------------+----------------------+

+-----------------------------------------------------------------------------+ | NVIDIA-SMI 535.104.05 Driver Version: 535.104.05 CUDA Version: 12.2 | |-------------------------------+----------------------+----------------------+ | GPU Name Persistence-M| Bus-Id Disp.A | Volatile Uncorr. ECC | | Fan Temp Perf Pwr:Usage/Cap| Memory-Usage | GPU-Util Compute M. | | 0 NVIDIA RTX 4090 On | 00000000:01:00.0 Off | Off | | 34% 65C P8 15W / 450W | 4000MiB / 24576MiB | 12% Default | +-------------------------------+----------------------+----------------------+

```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.104.05   Driver Version: 535.104.05   CUDA Version: 12.2     |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|   0  NVIDIA RTX 4090      On  | 00000000:01:00.0 Off |                  Off |
| 34%   65C    P8   15W / 450W  |  4000MiB / 24576MiB  |     12%      Default |
+-------------------------------+----------------------+----------------------+
```

Обновление «как top» через watch:

```
watch -n 2 nvidia-smi
```

Либо встроенный loop у самой утилиты: `nvidia-smi -l 2` (интервал в секундах).

## Версия драйвера и CUDA

Для скриптов удобнее машинночитаемый CSV через `--query-gpu` и `--format`:

nvidia-smi --query-gpu=driver\_version,cuda\_version --format=csv

nvidia-smi --query-gpu=driver\_version,cuda\_version --format=csv

```
nvidia-smi --query-gpu=driver_version,cuda_version --format=csv
```

Пример ответа:

driver\_version, cuda\_version

driver\_version, cuda\_version 535.104.05, 12.2

```
driver_version, cuda_version
535.104.05, 12.2
```

Поле `cuda_version` в nvidia-smi – это максимальная версия CUDA, которую заявляет _драйвер_, а не обязательно то, что установлено в `/usr/local/cuda`. Для точной версии toolkit смотрите `nvcc --version`, если toolkit реально стоит.

## Энергопотребление и power limit

Текущий draw:

nvidia-smi --query-gpu=power.draw,power.limit,power.max\_limit --format=csv

nvidia-smi --query-gpu=power.draw,power.limit,power.max\_limit --format=csv

```
nvidia-smi --query-gpu=power.draw,power.limit,power.max_limit --format=csv
```

Ограничить power limit (Вт), например до 100:

\# или для конкретной карты:

sudo nvidia-smi -i 0 -pl 100

sudo nvidia-smi -pl 100 # или для конкретной карты: sudo nvidia-smi -i 0 -pl 100

```
sudo nvidia-smi -pl 100
# или для конкретной карты:
sudo nvidia-smi -i 0 -pl 100
```

Лимит должен попадать в допустимый для модели диапазон (min/max limit). На многих системах нужны root-права и иногда включённый persistence mode. После ребута лимит часто сбрасывается – для постоянства обычно ставят unit/cron или включают persistence и скрипт на старте.

Persistence mode (драйвер не выгружается, быстрее «просыпается» GPU):

```
sudo nvidia-smi -pm 1
```

## Процессы на GPU

Кто держит карту – внизу обычного `nvidia-smi` или через process monitor:

```
nvidia-smi pmon -s um
```

Условный вид:

\# gpu pid type sm mem enc dec command

0 1245 C 50% ... 0 0 python3

\# gpu pid type sm mem enc dec command 0 1245 C 50% ... 0 0 python3 0 3765 G 5% ... 0 0 Xorg

```
# gpu   pid  type  sm   mem  enc  dec  command
  0    1245   C    50%  ...    0    0  python3
  0    3765   G     5%  ...    0    0  Xorg
```

-   **C** – compute (CUDA и подобные нагрузки);
-   **G** – graphics (Xorg, композитор, игры и т.п.);
-   **C+G** – смешанный тип, если показывается.

Список в CSV:

nvidia-smi --query-compute-apps=pid,process\_name,used\_memory --format=csv

nvidia-smi --query-compute-apps=pid,process\_name,used\_memory --format=csv

```
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

Зависший job – сначала мягко `kill PID`, при необходимости `kill -9 PID`. На shared-серверах сначала убедитесь, что процесс ваш: чужой CUDA-job «убивать» без договорённости – плохая идея.

## Логирование

Простой поток полного вывода каждые 5 секунд в файл:

nvidia-smi -l 5 > gpu\_log.txt

nvidia-smi -l 5 > gpu\_log.txt

```
nvidia-smi -l 5 > gpu_log.txt
```

Для метрик удобнее сразу query + CSV (его проще парсить и класть в Prometheus/Grafana через exporter или свой скрипт):

nvidia-smi --query-gpu=timestamp,name,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw --format=csv -l 5 > gpu\_metrics.csv

nvidia-smi --query-gpu=timestamp,name,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw --format=csv -l 5 > gpu\_metrics.csv

```
nvidia-smi --query-gpu=timestamp,name,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.total,power.draw --format=csv -l 5 > gpu_metrics.csv
```

Выборочный разбор уже записанного «красивого» лога:

grep -E 'MiB|%' gpu\_log.txt | head

grep -E 'MiB|%' gpu\_log.txt | head

```
grep -E 'MiB|%' gpu_log.txt | head
```

## Полезные query-поля

Частый набор для мониторинга одной строкой:

nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw,power.limit --format=csv,noheader,nounits

nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw,power.limit --format=csv,noheader,nounits

```
nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw,power.limit --format=csv,noheader,nounits
```

Полный список поддерживаемых полей:

nvidia-smi --help-query-gpu

nvidia-smi --help-query-gpu

```
nvidia-smi --help-query-gpu
```

## На что смотреть на практике

-   **Memory-Usage почти full, util низкий** – часто «утёк» или закеширован контекст, либо модель лежит в VRAM без активных kernel.
-   **Util 100%, power у cap** – карта упёрлась в лимит мощности или термолимиты (смотрите temp и throttling через dmesg/другие утилиты при необходимости).
-   **Несколько GPU** – `-i 0,1` или фильтр в query; проверяйте, что job сел на нужный device (`CUDA_VISIBLE_DEVICES`).
-   **MIG / vGPU** – вывод и возможности отличаются; для MIG есть отдельные режимы и query.

## Итог

`nvidia-smi` закрывает повседневные задачи: живая картина по загрузке и VRAM, версии драйвера, power limit, кто занимает GPU, простое логирование в CSV. Для продакшен-мониторинга кластера обычно дополняют DCGM, Prometheus nvidia\_gpu\_exporter или облачными агентами – но для отладки на конкретной машине достаточно одной утилиты из комплекта драйвера.

### Источники и ссылки

___

Cookie, аналитика и РСЯ включены. Можно отключить. [Политика](https://krivoshein.site/politika-v-otnoshenii-obrabotki-personalnyh-dannyh/)

## Настройка Cookies

Для сайта в РФ: по умолчанию всё включено. Можно оставить или отключить лишнее. Подробнее в [политике](https://krivoshein.site/politika-v-otnoshenii-obrabotki-personalnyh-dannyh/).

Необходимые

Работа сайта, тема light/dark, сохранение выбора.

Аналитика

Яндекс.Метрика и Top100: посещаемость, клики.

Рекомендации (РСЯ)

Рекомендательный виджет Яндекса в блоге и на сервисах.