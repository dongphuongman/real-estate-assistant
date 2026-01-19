**Цели**
- Зафиксировать разделение Core (Open Source) и Pro (Hosted) без утечки приватных планов.
- Обновить публичные документы (PRD, ARCHITECTURE, ROADMAP, DEPLOYMENT) только для Core.
- Подготовить приватные материалы в некоммитируемой директории для Pro.

**Текущее состояние**
- Публичные доки: [PRD.MD](file:///c:/Projects/ai-real-estate-assistant/docs/PRD.MD), [ARCHITECTURE.md](file:///c:/Projects/ai-real-estate-assistant/docs/ARCHITECTURE.md), [ROADMAP.md](file:///c:/Projects/ai-real-estate-assistant/docs/ROADMAP.md), [README.md](file:///c:/Projects/ai-real-estate-assistant/docs/README.md), [PROJECT_STRUCTURE.md](file:///c:/Projects/ai-real-estate-assistant/docs/PROJECT_STRUCTURE.md)
- Бэкенд: FastAPI ([main.py](file:///c:/Projects/ai-real-estate-assistant/api/main.py), роуты в api/routers)
- Фронтенд: Next.js + ShadcnUI ([frontend/package.json](file:///c:/Projects/ai-real-estate-assistant/frontend/package.json))
- Игнор: [.gitignore](file:///c:/Projects/ai-real-estate-assistant/.gitignore), [.dockerignore](file:///c:/Projects/ai-real-estate-assistant/.dockerignore)

**Публичные обновления (Core)**
- Обновить PRD для Core:
  - Чёткое разделение «Core vs Pro», BYOK для LLM, Local RAG, базовые промпты, локальный деплой, лицензия AGPLv3.
  - Указать расширяемые точки (интерфейсы провайдеров) без упоминания Pro-данных/интеграций.
- Обновить ARCHITECTURE.md:
  - Modular Monolith: UI → Agents → Providers → Vector Store → Data.
  - Интерфейсы в Core: provider_factory для LLM/CRM/valuation/data_enrichment/legal_check.
  - Реализации по умолчанию: локальные/заглушки, без внешних платных API.
  - Механизм feature flags для переключения реализаций (без публикации Pro-флагов).
- Обновить ROADMAP.md:
  - Этап 1 «Community Engine»: GitHub публикация, документация «запуск за 5 минут», issue для Telegram-коннектора, метрики OSS (stars/PRs).
  - Без упоминания Pro-данных и платных API.
- Обновить DEPLOYMENT.md:
  - Docker Compose (Self-hosted), env-переменные, BYOK (OpenAI ключ пользователя или Ollama/Llama 3), PostgreSQL схема.

**Приватные материалы (не коммитить)**
- Создать директорию: c:\Projects\ai-real-estate-assistant\private\ (будет добавлена в .gitignore).
- Поддиректории: private\notes\, private\adr\, private\pro_roadmap\, private\integrations\, private\legal_kb\, private\telephony\, private\analytics\.
- Приватные файлы:
  - Created: private\PRD_PRO.md
  - Created: private\ARCHITECTURE_PRO.md
  - Created: private\ROADMAP_PRO.md
  - Created: private\INTEGRATIONS.md (CRM: AmoCRM, Bitrix24, kvCORE; телефония)
  - Created: private\LEGAL_KB_PLAN.md (юридические кейсы и риск-модели)
  - Created: private\TELEPHONY_VOICE.md (потоки, провайдеры)
  - Created: private\ANALYTICS_DASHBOARD.md (метрики диалогов/конверсий)
- Игнор:
  - Updated: .gitignore (добавить private/ и поддиректории)
  - Updated: .dockerignore (исключить private/ из образов)

**Архитектура разделения (Core / Pro)**
- Core экспортирует интерфейсы:
  - llm_provider, rag_provider, valuation_provider, crm_connector, data_enrichment_service, legal_check_service.
- В Core реализации по умолчанию:
  - llm_provider: Ollama/Llama3 или BYOK ключ пользователя.
  - rag_provider: локальные файлы, Chroma/PGVector.
  - valuation_provider: простая формула/заглушка.
  - crm_connector: вебхуки.
  - data_enrichment_service: отключено/минимум открытые источники.
  - legal_check_service: базовые эвристики без закрытой базы.
- Pro (в private Repo B или /plugins):
  - Переопределяет интерфейсы: тонкие модели, платные API, двусторонние CRM коннекторы, телефонию, аналитическую панель.
  - Интеграция через явные адаптеры (HTTP/gRPC/Python entry points).

**Лицензии и комплаенс**
- Core: AGPLv3 (обязует модификаторов раскрывать исходники).
- Pro: проприетарная лицензия, данные и коннекторы не публикуем.
- Секреты только через env-переменные; приватные файлы без ключей.

**Запланированные изменения (пути)**
- Updated: docs\PRD.MD
- Updated: docs\ARCHITECTURE.md
- Updated: docs\ROADMAP.md
- Updated: docs\DEPLOYMENT.md
- Created: private\PRD_PRO.md
- Created: private\ARCHITECTURE_PRO.md
- Created: private\ROADMAP_PRO.md
- Created: private\INTEGRATIONS.md
- Created: private\LEGAL_KB_PLAN.md
- Created: private\TELEPHONY_VOICE.md
- Created: private\ANALYTICS_DASHBOARD.md
- Updated: .gitignore
- Updated: .dockerignore

**Риски и меры**
- Утечка Pro-планов: всё хранить в private/, добавлено в игноры.
- Сложность поддержки: строгие интерфейсы и адаптеры, минимальная связность.
- Лицензии: AGPLv3 для Core, проприетарная для Pro; проверка совместимости.

**Последовательность выполнения**
1) Обновить публичные доки (PRD, ARCHITECTURE, ROADMAP, DEPLOYMENT) для Core.
2) Добавить private/ в .gitignore и .dockerignore.
3) Создать приватные файлы по списку и перенести планы Pro.
4) Зафиксировать интерфейсы в Core (описание в ARCHITECTURE.md), без кода Pro.

Подтвердите план — после этого выполню изменения и размещу приватные документы в некоммитируемой директории.