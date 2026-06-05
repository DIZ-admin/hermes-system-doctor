# Hermes Agent System Doctor: зачем нужен и что умеет

GitHub: https://github.com/AlekseiUL/hermes-system-doctor

**Hermes Agent System Doctor** - локальный диагностический CLI для пользователей Hermes Agent, которым нужно проверить живую установку перед правками, обновлением или ремонтом.

Он не заменяет штатный `hermes doctor`. Штатный doctor проверяет базовую установку. Этот репозиторий добавляет отдельный safety-first слой вокруг реальной рабочей системы: профили, config, cron, gateway, logs, memory, skills, plugins, MCP и локальные признаки drift после обновлений.

Главная идея простая: сначала собрать факты, потом показать риск, потом подготовить repair-plan, и только после явного подтверждения делать узкое безопасное исправление.

## Для кого этот репозиторий

Repo полезен тем, кто:

- использует Hermes Agent не как один тестовый чат, а как рабочий контур;
- держит несколько профилей, cron jobs, skills, plugins или MCP servers;
- обновляет Hermes и хочет понять, что изменилось в системе;
- боится чинить config, не понимая, где реальная причина;
- хочет получить отчёт без дампа secrets, raw logs, cookies, auth payloads и приватной памяти.

В реальной работе агент ломается не только из-за модели. Часто проблема вокруг него: битый config, исчезнувший script, неверный workdir, странный cron, stale gateway PID, сломанный skill metadata, MCP config с недостающими env refs.

Doctor помогает увидеть это до того, как человек начнёт чинить вслепую.

## Что делает Doctor

Doctor запускается локально и строит безопасный отчёт по Hermes home.

Базовый поток работы:

```bash
hermes-system-doctor full --hermes-home ~/.hermes --json --output report.json
hermes-system-doctor repair-plan --input report.json --output repair-plan.json
hermes-system-doctor fix --hermes-home ~/.hermes --plan repair-plan.json --approve rp-0001
hermes-system-doctor fix --hermes-home ~/.hermes --plan repair-plan.json --approve rp-0001 --execute
hermes-system-doctor full --hermes-home ~/.hermes --json --output after.json
```

Смысл потока:

1. `full` собирает факты.
2. `repair-plan` превращает findings в действия с явным подтверждением.
3. `fix` показывает preview для выбранного action.
4. `fix --execute` применяет только зарегистрированный узкий executor.
5. Повторный `full` проверяет, ушёл ли finding.

## Что проверяется сейчас

### 1. Hermes home discovery

Doctor определяет локальный Hermes home и строит inventory рабочей системы.

Проверяет:

- существует ли Hermes home;
- корректно ли выглядит `profiles/`;
- есть ли root/default profile;
- есть ли named profiles;
- не уводят ли symlinks чтение за пределы разрешённого scope.

Если структура неожиданная, Doctor не падает traceback. Он отдаёт finding с понятным статусом.

### 2. Profiles inventory

Doctor смотрит профили как рабочие единицы, а не как абстрактные папки.

Проверяет:

- список профилей;
- profile path shape;
- root/default profile и named profiles;
- опасные path/symlink cases, которые component checks могут безопасно пропустить или вынести в finding;
- невозможность безопасно прочитать профиль.

Сырые приватные данные профиля не печатаются.

### 3. Config checks

Doctor проверяет `config.yaml` без попытки чинить его сразу.

Проверяет:

- есть ли `config.yaml`;
- парсится ли YAML;
- config не выглядит директорией или странным объектом;
- можно ли безопасно классифицировать проблему.

Текущий зарегистрированный executor связан именно с этим блоком: `config.missing`.

### 4. Cron checks

Doctor разбирает cron metadata без запуска jobs.

Проверяет:

- наличие cron jobs;
- ссылки на scripts;
- ссылки на workdir;
- relative scripts внутри profile `scripts/`;
- missing script;
- missing workdir;
- script paths, которые уходят за пределы profile;
- неожиданные cron shapes.

Cron jobs не запускаются. Никакие schedules не меняются.

### 5. Gateway checks

Doctor смотрит gateway как поверхность риска, но не трогает его.

Проверяет:

- config/log/PID сигналы;
- stale PID files;
- gateway log categories;
- наличие признаков проблем без raw log lines;
- локальные факты, которые можно проверить без network probes.

Doctor не рестартит gateway, не отправляет platform messages и не делает внешние проверки.

### 6. Logs diagnostics

Doctor читает logs ограниченно и безопасно.

Он не печатает raw log text.

Вместо этого отдаёт категории:

- auth errors;
- model/provider errors;
- import errors;
- compression errors;
- gateway errors;
- cron errors;
- memory errors;
- MCP errors;
- tool errors.

Для каждой категории можно увидеть count, safe file label и line number. Содержимое строки не раскрывается.

### 7. Auth surface inventory

Doctor ищет secret-adjacent surfaces, но не открывает payloads.

Проверяет наличие:

- `.env`;
- `auth.json`;
- cookie/session-like files;
- private-key-like files;
- token/auth files в неожиданных местах.

Он не валидирует credentials и не печатает secrets. Задача блока - показать, где есть чувствительная поверхность, которую нельзя случайно утащить в отчёт или репозиторий.

### 8. Memory checks

Doctor проверяет memory layer без чтения приватной памяти.

Проверяет:

- наличие memory files;
- ожидаемые memory surfaces;
- странные file shapes;
- дубликаты candidate files с учётом case-insensitive вариантов;
- безопасность labels.

Содержимое memory не дампится.

### 9. Skills checks

Doctor проверяет skills как рабочий слой Hermes.

Проверяет:

- skill discovery;
- bounded frontmatter parsing;
- обязательные metadata fields;
- duplicate skill names внутри одного profile;
- linked files integrity;
- linked-file path safety;
- странные skill shapes.

Skill bodies и linked-file contents не печатаются в отчёт.

### 10. Plugins checks

Doctor инвентаризирует plugins без исполнения кода.

Проверяет:

- plugin manifests;
- plugin directory shape;
- metadata shape;
- подозрительные или неполные declarations;
- отсутствие ожидаемых файлов.

Plugin code не импортируется и не запускается.

### 11. MCP checks

Doctor проверяет MCP config как локальную конфигурацию.

Проверяет:

- server config shape;
- transport shape;
- command/args/env/header references;
- `${VAR}` refs по именам env keys;
- missing или странные MCP declarations.

MCP servers не запускаются. MCP tools не вызываются. Network probes не выполняются.

### 12. Post-update drift checks

Doctor помогает после обновления Hermes понять, где могла появиться несовместимость.

Проверяет только локальные сигналы:

- local git-ref drift hints;
- локальные файлы и metadata;
- profile/config/runtime shape changes;
- признаки того, что нужна ручная проверка.

Doctor не делает `git fetch`, не импортирует runtime dependencies и не меняет систему.

### 13. Safe reporting

Doctor умеет отдавать JSON и Markdown отчёты.

Отчёт разделяет:

- fact;
- risk;
- unknown;
- finding;
- next action;
- approval required;
- not run facts.

Абсолютные приватные пути редактируются до safe labels. Secret-like payloads не попадают в report.

### 14. Repair plan

Команда `repair-plan` берёт JSON report и строит dry-run план ремонта.

План содержит:

- `action_id`;
- `finding_id`;
- component;
- severity;
- profile;
- mode;
- approval required;
- backup required;
- destructive flag;
- safe manual command;
- proposed change;
- rollback hint;
- risk;
- source evidence summary.

`repair-plan` ничего не пишет. Это план для человека или оператора.

### 15. Gated fix preview

Команда `fix` без `--execute` показывает, что будет сделано для конкретного action.

Она требует:

- `--plan`;
- `--approve action-id`;
- action из repair plan;
- registered executor для реального применения.

План считается untrusted input. Doctor не строит shell-команды из сырых полей report и не доверяет случайным строкам из входного файла.

### 16. Первый safe executor: `config.missing`

Сейчас есть один зарегистрированный mutating executor.

Он чинит только finding:

```text
config.missing
```

Что делает executor:

- требует явный `--hermes-home`;
- требует `--approve action-id`;
- создаёт минимальный parseable `config.yaml` stub;
- пишет backup manifest;
- проверяет path/symlink safety;
- не перезаписывает существующий config;
- не добавляет providers, API keys, model settings или secrets;
- не рестартит gateway;
- не запускает cron;
- не трогает MCP, plugins, memory или platform messages.

Это не общий auto-fix. Это первый доказуемый безопасный repair executor.

## Что Doctor специально не делает

Doctor не должен быть опасным.

Поэтому он не делает по умолчанию:

- restart services;
- gateway probes;
- platform messages;
- cron execution;
- plugin execution;
- MCP tool execution;
- credential validation;
- raw log dump;
- raw memory dump;
- cookie/session dump;
- broad auto-fix;
- network probes;
- destructive cleanup.

Если для проверки нужен доступ, внешний вызов или изменение системы, Doctor должен показать `UNKNOWN`, `not_run` или approval-required action, а не делать вид, что всё проверил.

## Чем это отличается от обычного `hermes doctor`

`hermes doctor` нужен для базовой проверки Hermes.

Hermes Agent System Doctor нужен для рабочего контура вокруг Hermes:

- несколько profiles;
- cron jobs;
- logs;
- gateway signals;
- memory layer;
- skills layer;
- plugins;
- MCP;
- auth surfaces;
- post-update drift;
- approval-gated repair planning;
- narrow safe executors.

То есть это не замена штатной команды. Это companion tool для тех, кто уже использует Hermes как рабочую систему и хочет видеть больше, чем “установилось или нет”.

## Почему это полезно

Когда агентная система растёт, обычный ответ “проверь config” уже не помогает.

Нужно понять:

- где факт;
- где гипотеза;
- где риск;
- где неизвестно;
- где нужно явное подтверждение;
- где можно чинить автоматически;
- где автоматический ремонт опасен.

Doctor делает этот слой видимым.

Он помогает не лезть руками в живую систему без карты. Сначала отчёт. Потом plan. Потом preview. Потом узкое исправление. Потом повторная проверка.

## Текущий статус

Текущая версия:

```text
v0.1.0 alpha / safety-first preview
```

Repo уже опубликован:

https://github.com/AlekseiUL/hermes-system-doctor

Release:

https://github.com/AlekseiUL/hermes-system-doctor/releases/tag/v0.1.0

Это уже можно показывать как рабочий public preview.

Но честная граница такая: это не полный универсальный автолекарь для любой Hermes-инсталляции. Это безопасный doctor, repair planner и первый узкий executor. Дальше executor'ы должны добавляться по одному, только после тестов backup/diff/rollback и review.

## Быстрый старт

```bash
git clone https://github.com/AlekseiUL/hermes-system-doctor
cd hermes-system-doctor
python -m pip install -e ".[dev]"
hermes-system-doctor full --hermes-home ~/.hermes --markdown --output doctor-report.md
```

Если нужен repair plan:

```bash
hermes-system-doctor full --hermes-home ~/.hermes --json --output report.json
hermes-system-doctor repair-plan --input report.json --output repair-plan.json
```

Если plan содержит action для registered executor:

```bash
hermes-system-doctor fix --hermes-home ~/.hermes --plan repair-plan.json --approve rp-0001
```

И только после проверки preview:

```bash
hermes-system-doctor fix --hermes-home ~/.hermes --plan repair-plan.json --approve rp-0001 --execute
```

## Коротко для публикации

Hermes Agent System Doctor - это локальный doctor для Hermes Agent, который проверяет не только базовую установку, а весь рабочий контур вокруг агента: profiles, config, cron, logs, memory, skills, plugins, MCP и gateway signals.

Он не дампит secrets, не читает raw auth payloads, не запускает plugins/MCP/cron и не делает broad auto-fix.

Сначала факты. Потом repair-plan. Потом preview. Потом только узкий approved fix.

GitHub:
https://github.com/AlekseiUL/hermes-system-doctor
