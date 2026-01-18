"""
AI Real Estate Assistant - Modern Version (V3) - Phases 1-5

A modernized real estate assistant with:
- Multiple model providers (OpenAI, Anthropic, Google, Grok, DeepSeek, Ollama)
- 25+ AI models across 6 providers
- Persistent vector storage with ChromaDB
- Intelligent hybrid agent (RAG + Tools)
- Query analysis and routing
- Result reranking
- Personalized recommendations
- Modern UI with enhanced features (multi-language, dark/light themes)
- Type-safe data models with Pydantic
- Market insights and analytics (Phase 3)
- Export functionality (Phase 3)
- Saved searches and comparisons (Phase 3)
- Advanced visualizations (Phase 4)
- Notification system with email alerts (Phase 5)

Copyright (c) 2025 Alex Nesterovich
GitHub: https://github.com/AleksNeStu/ai-real-estate-assistant
"""

import logging
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# Phase 2 imports
from agents.query_analyzer import analyze_query
from agents.recommendation_engine import create_recommendation_engine
from ai.app_services import create_conversation_chain as svc_create_conversation_chain
from ai.app_services import create_hybrid_agent_instance as svc_create_hybrid_agent_instance
from ai.app_services import create_llm as svc_create_llm
from ai.app_services import create_property_retriever as svc_create_property_retriever

# Phase 3 imports
from analytics import EventType, MarketInsights, SessionTracker

# Import our custom modules
from config import settings, update_api_key
from data.csv_loader import DataLoaderCsv
from data.schemas import Property, PropertyCollection
from data.providers.factory import DataProviderFactory

# Internationalization
from i18n import get_available_languages, get_text
from models.provider_factory import ModelProviderFactory, get_model_display_info

# Phase 5 imports
from notifications import (
    AlertFrequency,
    DigestDay,
    EmailConfig,
    EmailProvider,
    EmailService,
    EmailServiceFactory,
    NotificationHistory,
    NotificationPreferencesManager,
    TestEmailTemplate,
)
from streaming import StreamHandler
from ui.dev_dashboard import render_dev_dashboard
from ui.geo_viz import (
    _get_city_coordinates,
    create_historical_trends_map,
    create_property_map,
    create_price_heatmap,
    create_city_overview_map,
)
from utils import (
    ExportFormat,
    InsightsExporter,
    PropertyExporter,
    SavedSearchManager,
    ParallelDataLoader,
    inject_enhanced_form_styles,
    inject_tailwind_cdn,
    load_and_inject_styles,
)
from utils.api_key_validator import APIKeyValidator
from utils.ollama_detector import OllamaDetector
from vector_store.chroma_store import get_vector_store
from vector_store.reranker import create_reranker
from notifications.scheduler import NotificationScheduler
from ui.comparison_dashboard import display_comparison_dashboard

# LangChain imports

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title=settings.app_title,
    page_icon=settings.app_icon,
    layout=settings.page_layout,
    initial_sidebar_state="expanded",
)

# Load and inject custom styles for dark mode and modern UI
load_and_inject_styles()
inject_enhanced_form_styles()
inject_tailwind_cdn()


@st.cache_resource
def get_digest_scheduler():
    email_service = EmailServiceFactory.create_from_env()
    if email_service is None:
        return None
    
    # Initialize dependencies
    vector_store = get_vector_store()
    
    scheduler = NotificationScheduler(
        email_service=email_service,
        vector_store=vector_store
    )
    scheduler.start()
    return scheduler


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "vector_store" not in st.session_state:
        st.session_state.vector_store = None

    if "property_collection" not in st.session_state:
        try:
            from utils.property_cache import load_collection

            cached = load_collection()
        except Exception:
            cached = None
        st.session_state.property_collection = cached

    if "selected_provider" not in st.session_state:
        st.session_state.selected_provider = "openai"

    if "selected_model" not in st.session_state:
        st.session_state.selected_model = "gpt-4o-mini"

    if "conversation_chain" not in st.session_state:
        st.session_state.conversation_chain = None

    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = bool(st.session_state.property_collection)

    try:
        get_digest_scheduler()
    except Exception:
        pass

    if st.session_state.property_collection is not None and st.session_state.vector_store is None:
        try:
            load_into_vector_store(st.session_state.property_collection)
        except Exception:
            pass

    # Phase 2 state variables
    if "use_hybrid_agent" not in st.session_state:
        st.session_state.use_hybrid_agent = True

    if "show_query_analysis" not in st.session_state:
        st.session_state.show_query_analysis = False

    if "use_reranking" not in st.session_state:
        st.session_state.use_reranking = True

    if "reranking_strategy" not in st.session_state:
        st.session_state.reranking_strategy = "balanced"

    if "reranker" not in st.session_state:
        # Create reranker with valuation model if available
        # Ideally we would pass the actual valuation model here
        # For now we create it without model, or we could initialize it later
        st.session_state.reranker = create_reranker()

    if "hybrid_agent" not in st.session_state:
        st.session_state.hybrid_agent = None

    if "recommendation_engine" not in st.session_state:
        st.session_state.recommendation_engine = create_recommendation_engine()

    # Phase 3 state variables
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    if "session_tracker" not in st.session_state:
        st.session_state.session_tracker = SessionTracker(st.session_state.session_id)

    if "search_manager" not in st.session_state:
        st.session_state.search_manager = SavedSearchManager()

    if "market_insights" not in st.session_state:
        if st.session_state.property_collection is not None:
            st.session_state.market_insights = MarketInsights(st.session_state.property_collection)
        else:
            st.session_state.market_insights = None

    if "selected_properties_for_comparison" not in st.session_state:
        st.session_state.selected_properties_for_comparison = []

    # Phase 5 state variables
    if "notification_prefs_manager" not in st.session_state:
        st.session_state.notification_prefs_manager = NotificationPreferencesManager()

    if "notification_history" not in st.session_state:
        st.session_state.notification_history = NotificationHistory()

    if "email_service" not in st.session_state:
        st.session_state.email_service = None

    if "user_email" not in st.session_state:
        st.session_state.user_email = ""

    # Language support
    if "language" not in st.session_state:
        st.session_state.language = "en"

    # Theme support
    if "theme" not in st.session_state:
        # Default to light theme
        st.session_state.theme = "light"

    # Auto-load default datasets on first run
    try:
        if "autoload_default_datasets" not in st.session_state:
            st.session_state.autoload_default_datasets = settings.autoload_default_datasets
        if (
            not st.session_state.data_loaded
            and st.session_state.autoload_default_datasets
            and settings.default_datasets
        ):
            urls_text = "\n".join(settings.default_datasets)
            load_data_from_urls(urls_text)
    except Exception:
        pass


def render_sidebar():
    """Render sidebar with model selection and configuration."""
    with st.sidebar:
        lang = st.session_state.language
        st.title(f"{settings.app_icon} {get_text('app_title', lang)}")
        st.caption(f"{get_text('version', lang)} {settings.version}")

        # Preferences (collapsible)
        with st.expander(f"⚙️ {get_text('preferences', lang)}", expanded=True):
            languages = get_available_languages()
            selected_lang = st.selectbox(
                get_text("language", lang),
                options=list(languages.keys()),
                format_func=lambda x: languages[x],
                index=list(languages.keys()).index(st.session_state.language),
                key="language_selector",
                label_visibility="collapsed",
            )
            if selected_lang != st.session_state.language:
                st.session_state.language = selected_lang
                st.rerun()

        with st.expander(f"🔔 {get_text('notification_settings', lang)}", expanded=False):
            current_email = st.session_state.user_email
            new_email = st.text_input(get_text("your_email", lang), value=current_email, key="notification_email_input")
            
            if new_email != current_email:
                st.session_state.user_email = new_email
                if st.session_state.notification_prefs_manager:
                    st.session_state.notification_prefs_manager.get_preferences(new_email)
            
            if st.session_state.user_email:
                prefs_manager = st.session_state.notification_prefs_manager
                user_prefs = prefs_manager.get_preferences(st.session_state.user_email)
                
                notifications_enabled = st.checkbox(
                    get_text("enable_notifications", lang),
                    value=user_prefs.email_enabled,
                    key="notifications_enabled_toggle"
                )
                
                freq_options = [f.value for f in AlertFrequency]
                freq_label_key_by_value = {
                    AlertFrequency.INSTANT.value: "instant",
                    AlertFrequency.HOURLY.value: "hourly",
                    AlertFrequency.DAILY.value: "daily_digest",
                    AlertFrequency.WEEKLY.value: "weekly_digest",
                }
                selected_freq = st.selectbox(
                    get_text("alert_frequency", lang),
                    options=freq_options,
                    format_func=lambda x: get_text(freq_label_key_by_value.get(x, x), lang),
                    index=freq_options.index(user_prefs.digest_frequency) if user_prefs.digest_frequency in freq_options else 0,
                    key="digest_freq_select"
                )
                
                if selected_freq == AlertFrequency.WEEKLY.value:
                    day_options = [d.value for d in DigestDay]
                    selected_day = st.selectbox(
                        get_text("weekly_digest_day", lang),
                        options=day_options,
                        format_func=lambda x: get_text(x, lang),
                        index=day_options.index(user_prefs.digest_day) if user_prefs.digest_day in day_options else 0,
                        key="digest_day_select"
                    )
                else:
                    selected_day = user_prefs.digest_day

                instant_alerts = st.checkbox(
                    get_text("price_drop_alerts", lang),
                    value=user_prefs.instant_alerts_enabled,
                    key="instant_alerts_toggle"
                )
                
                if st.button(get_text("save_preferences", lang), key="save_notification_prefs"):
                    updated_prefs = user_prefs
                    updated_prefs.email_enabled = notifications_enabled
                    updated_prefs.digest_frequency = selected_freq
                    updated_prefs.digest_day = selected_day
                    updated_prefs.instant_alerts_enabled = instant_alerts
                    
                    prefs_manager.update_preferences(st.session_state.user_email, updated_prefs)
                    st.success(get_text("preferences_saved", lang))
                    
                if st.button(get_text("send_test_email", lang), key="send_test_email"):
                    if st.session_state.email_service:
                        with st.spinner(get_text("sending_test_email", lang)):
                            success = st.session_state.email_service.send_test_email(
                                st.session_state.user_email,
                                user_name="User"
                            )
                            if success:
                                st.success(get_text("test_email_success", lang))
                            else:
                                st.error(get_text("test_email_error", lang))
                    else:
                        st.error(get_text("email_config_error", lang))
            else:
                st.info(get_text("email_help", lang))

        st.divider()

        # Model Provider Selection (collapsible)
        with st.expander(f"🧩 {get_text('model_config', lang)}", expanded=True):
            # Get available providers
            providers = ModelProviderFactory.list_providers()
            provider_display = {
                "openai": "OpenAI",
                "anthropic": "Anthropic (Claude)",
                "google": "Google (Gemini)",
                "grok": "Grok (xAI)",
                "deepseek": "DeepSeek",
                "ollama": "Ollama (Local)",
            }

            # Auto-select Ollama if available and running (default for local models)
            default_provider_index = 0
            if "ollama" in providers and "selected_provider" not in st.session_state:
                ollama_status = OllamaDetector.get_status()
                if ollama_status.is_running and ollama_status.available_models:
                    default_provider_index = providers.index("ollama")
                    st.info("ℹ️ Ollama detected and set as default provider (free local AI models)")

            selected_provider = st.selectbox(
                get_text("provider", lang),
                options=providers,
                format_func=lambda x: provider_display.get(x, x),
                index=default_provider_index,
                key="provider_select",
            )

            st.session_state.selected_provider = selected_provider

            # Get provider instance
            provider = ModelProviderFactory.get_provider(selected_provider)

            # Ollama-specific: Detection and Installation Guidance
            if selected_provider == "ollama":
                st.subheader(f"🔧 {get_text('ollama_status', lang)}")
                with st.container():
                    ollama_status = OllamaDetector.get_status()

                    if ollama_status.is_installed:
                        st.success(get_text("ollama_installed", lang))
                        if ollama_status.version:
                            st.write(
                                f"**{get_text('ollama_version', lang)}:** {ollama_status.version}"
                            )

                        if ollama_status.is_running:
                            st.success(get_text("ollama_running", lang))
                            if ollama_status.available_models:
                                st.write(
                                    f"**{get_text('ollama_models_available', lang)}:** {len(ollama_status.available_models)}"
                                )
                                if len(ollama_status.available_models) <= 10:
                                    st.write(", ".join(ollama_status.available_models))
                        else:
                            st.warning(get_text("ollama_not_running", lang))
                            st.code(f"{get_text('ollama_start_service', lang)}: ollama serve")
                    else:
                        st.error(get_text("ollama_not_installed", lang))
                        st.info(get_text("ollama_install_instructions", lang))

                        # Get OS-specific installation instructions
                        os_type = OllamaDetector.get_os_type()
                        instructions = OllamaDetector.get_installation_instructions(os_type)

                        st.markdown(f"### {instructions.get('title', 'Installation')}")

                        # Method 1 (Recommended)
                        method_1 = instructions.get("method_1", {})
                        if method_1:
                            st.markdown(f"**{method_1.get('name', 'Method 1')}:**")
                            for step in method_1.get("steps", []):
                                st.write(f"- {step}")
                            if "url" in method_1:
                                st.link_button(get_text("ollama_download", lang), method_1["url"])
                            if "command" in method_1:
                                st.code(method_1["command"], language="bash")

                        # Show recommended models
                        st.markdown(f"**{get_text('ollama_recommended_models', lang)}:**")
                        recommended_models = OllamaDetector.get_recommended_models()
                        for model in recommended_models:
                            if model.get("recommended", False):
                                st.write(
                                    f"- `{model['name']}` - {model['description']} ({model['size']}, RAM: {model['ram']})"
                                )
                                st.code(
                                    f"{get_text('ollama_pull_model', lang)}: {model['command']}"
                                )

            # API Key Management for remote providers
            elif provider.requires_api_key:
                # Check if API key exists
                api_key_env = {
                    "openai": settings.openai_api_key,
                    "anthropic": settings.anthropic_api_key,
                    "google": settings.google_api_key,
                    "grok": None,  # Will use XAI_API_KEY or GROK_API_KEY from env
                    "deepseek": None,  # Will use DEEPSEEK_API_KEY from env
                }.get(selected_provider)

                # Initialize session state for API key management
                if f"{selected_provider}_key_status" not in st.session_state:
                    st.session_state[f"{selected_provider}_key_status"] = None

                st.subheader(f"🔑 {get_text('api_key_settings', lang)}")
                with st.container():
                    if api_key_env:
                        # Show key status
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            st.success(
                                f"✓ {provider.display_name} {get_text('api_key_configured', lang)}"
                            )
                        with col2:
                            if st.button(
                                get_text("validate_api_key", lang),
                                key=f"validate_{selected_provider}",
                            ):
                                with st.spinner(get_text("validating_key", lang)):
                                    result = APIKeyValidator.validate_key(
                                        selected_provider, api_key_env
                                    )
                                    st.session_state[f"{selected_provider}_key_status"] = result
                        with col3:
                            if st.button(
                                get_text("change_api_key", lang), key=f"change_{selected_provider}"
                            ):
                                st.session_state[f"{selected_provider}_show_change"] = True

                        # Show validation result
                        if st.session_state[f"{selected_provider}_key_status"]:
                            result = st.session_state[f"{selected_provider}_key_status"]
                            if result.is_valid:
                                st.success(f"{get_text('key_valid', lang)}: {result.message}")
                            else:
                                st.error(f"{get_text('key_invalid', lang)}: {result.message}")
                                if result.error_details:
                                    show_details = st.checkbox(
                                        "Error Details", key=f"err_details_{selected_provider}"
                                    )
                                    if show_details:
                                        st.code(result.error_details)

                        # Show change API key form if requested
                        if st.session_state.get(f"{selected_provider}_show_change", False):
                            st.markdown(f"**{get_text('enter_new_api_key', lang)}:**")
                            new_key = st.text_input(
                                f"New {provider.display_name} API Key",
                                type="password",
                                key=f"new_key_{selected_provider}",
                            )
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(
                                    get_text("save_api_key", lang), key=f"save_{selected_provider}"
                                ):
                                    if new_key:
                                        # Validate before saving
                                        with st.spinner(get_text("validating_key", lang)):
                                            result = APIKeyValidator.validate_key(
                                                selected_provider, new_key
                                            )
                                            if result.is_valid:
                                                update_api_key(selected_provider, new_key)
                                                ModelProviderFactory.clear_cache()
                                                st.success(get_text("api_key_saved", lang))
                                                st.session_state[
                                                    f"{selected_provider}_show_change"
                                                ] = False
                                                st.session_state[
                                                    f"{selected_provider}_key_status"
                                                ] = result
                                                st.rerun()
                                            else:
                                                st.error(
                                                    f"{get_text('api_key_validation_failed', lang)}: {result.message}"
                                                )
                                    else:
                                        st.warning(get_text("enter_new_api_key", lang))
                            with col2:
                                if st.button(
                                    get_text("cancel", lang), key=f"cancel_{selected_provider}"
                                ):
                                    st.session_state[f"{selected_provider}_show_change"] = False
                                    st.rerun()
                    else:
                        # No API key set - show input
                        st.warning(
                            f"{get_text('api_key_required', lang).format(provider=provider.display_name)}"
                        )
                        api_key = st.text_input(
                            f"{provider.display_name} API Key",
                            type="password",
                            help=f"Enter your {provider.display_name} API key",
                            key=f"input_{selected_provider}",
                        )
                        if st.button(
                            get_text("save_api_key", lang), key=f"save_new_{selected_provider}"
                        ):
                            if api_key:
                                # Validate before saving
                                with st.spinner(get_text("validating_key", lang)):
                                    result = APIKeyValidator.validate_key(
                                        selected_provider, api_key
                                    )
                                    if result.is_valid:
                                        update_api_key(selected_provider, api_key)
                                        ModelProviderFactory.clear_cache()
                                        st.success(get_text("api_key_saved", lang))
                                        st.session_state[f"{selected_provider}_key_status"] = result
                                        st.rerun()
                                    else:
                                        st.error(
                                            f"{get_text('api_key_validation_failed', lang)}: {result.message}"
                                        )
                                        if result.error_details:
                                            show_details_new = st.checkbox(
                                                "Error Details",
                                                key=f"err_details_new_{selected_provider}",
                                            )
                                            if show_details_new:
                                                st.code(result.error_details)
                            else:
                                st.warning(
                                    get_text("enter_api_key", lang).format(
                                        provider=provider.display_name
                                    )
                                )
            else:
                # Local provider - no API key needed
                st.info(f"ℹ️ {get_text('no_api_key_needed', lang)}")

            # Model selection
            models = provider.list_models()
            model_options = {m.id: m for m in models}

            selected_model_id = st.selectbox(
                get_text("model", lang),
                options=list(model_options.keys()),
                format_func=lambda x: model_options[x].display_name,
                key="model_select",
            )

            st.session_state.selected_model = selected_model_id

            # Display model info
            model_info = model_options[selected_model_id]
            st.subheader(f"ℹ️ {get_text('model_details', lang)}")
            with st.container():
                info = get_model_display_info(model_info)
                st.write(f"**{get_text('context', lang)}:** {info['context']}")
                st.write(f"**{get_text('cost', lang)}:** {info['cost']}")
                if "description" in info:
                    st.write(f"**{get_text('description', lang)}:** {info['description']}")
                if "recommended_for" in info:
                    st.write(
                        f"**{get_text('best_for', lang)}:**", ", ".join(info["recommended_for"])
                    )

        # Advanced settings (collapsible)
        with st.expander(f"⚙️ {get_text('advanced_settings', lang)}"):
            temperature = st.slider(
                get_text("temperature", lang),
                min_value=0.0,
                max_value=2.0,
                value=settings.default_temperature,
                step=0.1,
                help=get_text("controls_randomness", lang),
            )
            st.session_state.temperature = temperature

            max_tokens = st.number_input(
                get_text("max_tokens", lang),
                min_value=256,
                max_value=32000,
                value=settings.default_max_tokens,
                step=256,
                help=get_text("maximum_response_length", lang),
            )
            st.session_state.max_tokens = max_tokens

            k_results = st.slider(
                get_text("results_to_retrieve", lang),
                min_value=1,
                max_value=20,
                value=settings.default_k_results,
                help=get_text("num_properties_search", lang),
            )
            st.session_state.k_results = k_results

        # Intelligence features (collapsible)
        with st.expander(get_text("intelligence_features", lang)):
            use_hybrid_agent = st.checkbox(
                get_text("use_hybrid_agent", lang),
                value=st.session_state.use_hybrid_agent,
                help=get_text("enable_intelligent_routing", lang),
            )
            st.session_state.use_hybrid_agent = use_hybrid_agent

            show_query_analysis = st.checkbox(
                get_text("show_query_analysis", lang),
                value=st.session_state.show_query_analysis,
                help=get_text("display_query_intent", lang),
            )
            st.session_state.show_query_analysis = show_query_analysis

            use_reranking = st.checkbox(
                get_text("use_reranking", lang),
                value=st.session_state.use_reranking,
                help=get_text("rerank_better_relevance", lang),
            )
            st.session_state.use_reranking = use_reranking

            if use_reranking:
                strategy_options = {
                    "balanced": "Balanced",
                    "investor": "Investor (Yield/Price)",
                    "family": "Family (Space/Amenities)",
                    "bargain": "Bargain (Price)",
                }
                
                selected_strategy = st.selectbox(
                    "Reranking Strategy",
                    options=list(strategy_options.keys()),
                    format_func=lambda x: strategy_options[x],
                    index=list(strategy_options.keys()).index(st.session_state.reranking_strategy),
                    key="reranking_strategy_select"
                )
                st.session_state.reranking_strategy = selected_strategy

            if use_hybrid_agent:
                st.caption(f"✨ {get_text('agent_tools', lang)}")

        st.divider()

        # Data Source Management (collapsible)
        with st.expander(f"📊 {get_text('data_sources', lang)}"):
            autoload_flag = st.checkbox(
                "autoload_default_at_seton_start",
                value=st.session_state.get(
                    "autoload_default_datasets", settings.autoload_default_datasets
                ),
            )
            st.session_state.autoload_default_datasets = autoload_flag

            data_source_tab = st.radio(
                get_text("data_source", lang),
                options=["URL", get_text("local_files", lang)],
                horizontal=True,
            )

            if data_source_tab == "URL":
                csv_urls = st.text_area(
                    get_text("csv_urls", lang),
                    value="\n".join(settings.default_datasets),
                    placeholder=get_text("csv_urls_placeholder", lang),
                    help=get_text("csv_urls_help", lang),
                    height=100,
                )

                if st.button(get_text("load_data", lang), type="primary"):
                    if csv_urls:
                        load_data_from_urls(csv_urls)
                    else:
                        st.warning(get_text("please_enter_csv_url", lang))

            else:
                st.write(get_text("upload_csv_files", lang))
                uploaded_files = st.file_uploader(
                    "Choose CSV or Excel files",
                    type=["csv", "xlsx", "xls"],
                    accept_multiple_files=True,
                    label_visibility="collapsed",
                )

                if st.button(get_text("load_local_files", lang), type="primary"):
                    if uploaded_files:
                        load_local_files(uploaded_files)
                    else:
                        st.warning(get_text("please_upload_files", lang))

            # Data status
            if st.session_state.data_loaded:
                st.success(
                    f"✓ {get_text('data_loaded_success', lang)}: {len(st.session_state.property_collection.properties)} {get_text('properties', lang)}"
                )

                # Vector store stats
                if st.session_state.vector_store:
                    index_future = st.session_state.get("vector_store_index_future")
                    if index_future is not None and not index_future.done():
                        st.caption("Indexing properties in background…")
                    elif index_future is not None and index_future.done():
                        try:
                            index_future.result()
                        except Exception as e:
                            st.warning(f"Vector store indexing failed: {e}")
                        st.session_state.vector_store_index_future = None
                    stats = st.session_state.vector_store.get_stats()
                    st.info(
                        f"📦 {get_text('vector_store', lang)}: {stats.get('total_documents', 0)} {get_text('documents', lang)}"
                    )

        st.divider()

        # Session Management (collapsible)
        with st.expander(f"🔄 {get_text('session', lang)}"):
            col1, col2 = st.columns(2)
            with col1:
                if st.button(get_text("clear_chat", lang), use_container_width=True):
                    st.session_state.messages = []
                    st.session_state.conversation_chain = None
                    st.rerun()

            with col2:
                if st.button(get_text("reset_all", lang), use_container_width=True):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()


def load_data_from_urls(urls_text: str):
    """Load property data from multiple URLs."""
    lang = st.session_state.language

    # Parse URLs (one per line)
    urls = [url.strip() for url in urls_text.strip().split("\n") if url.strip()]

    if not urls:
        st.warning(get_text("please_enter_csv_url", lang))
        return

    all_properties = []
    success_count = 0
    failed_urls = []

    with st.spinner(get_text("loading_data_url", lang)):
        for i, url in enumerate(urls, 1):
            try:
                st.info(f"{get_text('url_processing', lang)} {i}/{len(urls)}: {url[:80]}...")

                # Load Data (CSV/JSON)
                provider = DataProviderFactory.create_provider(url)

                # Check for GitHub URL conversion (informational, logic handled in provider)
                if 'github.com' in url and '/blob/' in url:
                    st.info("🔗 Converting GitHub URL to raw format")

                df = provider.load_data()
                st.info(f"📊 Loaded {len(df)} rows")

                # Format/Normalize DataFrame columns (snake_case, defaults)
                # Note: CSVDataProvider does this internally, but JSON might not.
                # Running it again is safe and ensures consistency.
                df_formatted = DataLoaderCsv.format_df(df)
                st.info(f"✨ Formatted {len(df_formatted)} properties")

                # Convert to PropertyCollection
                collection_part = PropertyCollection.from_dataframe(df_formatted, source=url)

                all_properties.extend(collection_part.properties)
                success_count += 1
                st.success(
                    f"✓ {get_text('url_success', lang)}: {len(collection_part.properties)} {get_text('properties', lang)}"
                )

            except Exception as e:
                failed_urls.append((url, str(e)))
                st.error(f"❌ {get_text('url_failed', lang)}: {url[:80]}")
                st.error(f"Error: {str(e)}")
                # Continue processing other URLs
                continue

    # Show summary
    if all_properties:
        if st.session_state.property_collection:
            existing_props = st.session_state.property_collection.properties
        else:
            existing_props = []

        merged_map = {}
        for p in existing_props:
            merged_map[p.id or str(uuid.uuid4())] = p
        for p in all_properties:
            merged_map[p.id or str(uuid.uuid4())] = p

        merged_list = list(merged_map.values())
        combined_collection = PropertyCollection(
            properties=merged_list, total_count=len(merged_list)
        )
        st.session_state.property_collection = combined_collection
        try:
            from utils.property_cache import save_collection

            save_collection(combined_collection)
        except Exception:
            pass

        load_into_vector_store(combined_collection)

        # Create market insights (Phase 3)
        st.session_state.market_insights = MarketInsights(combined_collection)

        st.success(
            f"✓ {get_text('data_loaded_success', lang)}: {len(combined_collection.properties)} {get_text('properties', lang)} from {success_count}/{len(urls)} URLs!"
        )
        st.session_state.data_loaded = True

        # Show failed URLs summary if any
        if failed_urls:
            with st.expander(f"⚠️ Failed URLs ({len(failed_urls)})"):
                for url, error in failed_urls:
                    st.write(f"**{url}**")
                    st.code(error)
    else:
        st.error("❌ All URLs failed to load. Please check your URLs and try again.")
        if failed_urls:
            with st.expander("🔍 Error Details"):
                for url, error in failed_urls:
                    st.write(f"**{url}**")
                    st.code(error)


def load_local_files(uploaded_files):
    """Load property data from uploaded CSV/Excel files."""
    lang = st.session_state.language

    try:
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(progress: float, message: str):
            progress_bar.progress(progress)
            status_text.text(message)

        with st.spinner(get_text("loading_local_files", lang)):
            # Use ParallelDataLoader for faster processing
            loader = ParallelDataLoader(max_workers=min(len(uploaded_files), 4))
            collections = loader.load_files(uploaded_files, progress_callback=update_progress)
            
            all_properties = []
            
            for i, collection in enumerate(collections):
                all_properties.extend(collection.properties)
                # Show summary for each file
                st.toast(f"✅ Loaded {len(collection.properties)} properties from file {i+1}")

            if all_properties:
                if st.session_state.property_collection:
                    existing_props = st.session_state.property_collection.properties
                else:
                    existing_props = []

                merged_map = {}
                for p in existing_props:
                    merged_map[p.id or str(uuid.uuid4())] = p
                for p in all_properties:
                    merged_map[p.id or str(uuid.uuid4())] = p

                merged_list = list(merged_map.values())
                combined_collection = PropertyCollection(
                    properties=merged_list, total_count=len(merged_list)
                )
                st.session_state.property_collection = combined_collection
                try:
                    from utils.property_cache import save_collection

                    save_collection(combined_collection)
                except Exception:
                    pass

                load_into_vector_store(combined_collection)

                # Create market insights (Phase 3)
                st.session_state.market_insights = MarketInsights(combined_collection)

                st.success(
                    f"✓ {get_text('data_loaded_success', lang)}: {len(combined_collection.properties)} {get_text('properties', lang)}!"
                )
                st.session_state.data_loaded = True
            else:
                st.warning(f"{get_text('no_data', lang)}")
        
        # Clear progress
        progress_bar.empty()
        status_text.empty()

    except Exception as e:
        logger.error(f"Error loading files: {e}")
        st.error(f"❌ {get_text('error_occurred', lang)}: {str(e)}")
        # Show more details in an expander
        with st.expander("🔍 Error Details"):
            st.code(str(e))
            st.write("**Tip:** Make sure the CSV file has proper property data columns.")


def load_into_vector_store(collection: PropertyCollection):
    """Load property collection into vector store."""
    try:
        # Get or create vector store
        if st.session_state.vector_store is None:
            st.session_state.vector_store = get_vector_store()

        if getattr(st.session_state.vector_store, "vector_store", None) is None:
            # Try to re-initialize if it was previously failed or None
            st.session_state.vector_store = get_vector_store()

        index_future = st.session_state.get("vector_store_index_future")
        if index_future is not None and not index_future.done():
            st.toast("Background indexing is already in progress...", icon="⏳")
            return

        # Add properties
        vector_store = st.session_state.vector_store
        
        # Check if vector store is capable of indexing
        if vector_store:
            st.session_state.vector_store_index_future = vector_store.add_property_collection_async(
                collection,
                replace_existing=False,
            )
            st.toast("Started background indexing. You can continue searching.", icon="🚀")
            logger.info("Started background indexing for vector store")
        else:
             st.warning("Vector store is not available. Properties will be searched via simple cache only.")

    except Exception as e:
        logger.error(f"Error triggering vector store indexing: {e}")
        st.error(f"Could not start indexing: {e}")
        # Don't raise, just let the app continue with whatever data it has


def create_conversation_chain():
    """Create conversational retrieval chain (simple RAG mode)."""
    try:
        # Get model configuration
        provider_name = st.session_state.selected_provider
        model_id = st.session_state.selected_model
        temperature = st.session_state.get("temperature", settings.default_temperature)
        max_tokens = st.session_state.get("max_tokens", settings.default_max_tokens)
        k_results = st.session_state.get("k_results", settings.default_k_results)

        stream_handler = StreamHandler(st.empty())
        llm = svc_create_llm(
            provider_name=provider_name,
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=True,
            callbacks=[stream_handler],
        )

        use_reranking = st.session_state.get("use_reranking", True)
        reranker = st.session_state.get("reranker") if use_reranking else None
        strategy = st.session_state.get("reranking_strategy", "balanced")

        retriever = svc_create_property_retriever(
            vector_store=st.session_state.vector_store,
            k_results=k_results,
            center_lat=st.session_state.get("geo_center_lat"),
            center_lon=st.session_state.get("geo_center_lon"),
            radius_km=st.session_state.get("geo_radius_km"),
            listing_type_filter=st.session_state.get("listing_type_filter"),
            min_price=st.session_state.get("retr_min_price"),
            max_price=st.session_state.get("retr_max_price"),
            sort_by=st.session_state.get("retr_sort_by"),
            sort_ascending=st.session_state.get("retr_sort_ascending", True),
            year_built_min=st.session_state.get("retr_year_built_min"),
            year_built_max=st.session_state.get("retr_year_built_max"),
            energy_certs=st.session_state.get("retr_energy_certs"),
            must_have_parking=bool(st.session_state.get("retr_must_parking", False)),
            must_have_elevator=bool(st.session_state.get("retr_must_elevator", False)),
            reranker=reranker,
            strategy=strategy,
        )

        return svc_create_conversation_chain(
            llm=llm,
            retriever=retriever,
            verbose=True,
        )

    except Exception as e:
        st.error(f"Error creating conversation chain: {e}")
        return None


def create_hybrid_agent_instance():
    """Create hybrid agent instance (Phase 2)."""
    try:
        # Get model configuration
        provider_name = st.session_state.selected_provider
        model_id = st.session_state.selected_model
        temperature = st.session_state.get("temperature", settings.default_temperature)
        max_tokens = st.session_state.get("max_tokens", settings.default_max_tokens)
        k_results = st.session_state.get("k_results", settings.default_k_results)

        llm = svc_create_llm(
            provider_name=provider_name,
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=False,
        )

        use_reranking = st.session_state.get("use_reranking", True)
        reranker = st.session_state.get("reranker") if use_reranking else None
        strategy = st.session_state.get("reranking_strategy", "balanced")

        retriever = svc_create_property_retriever(
            vector_store=st.session_state.vector_store,
            k_results=k_results,
            center_lat=st.session_state.get("geo_center_lat"),
            center_lon=st.session_state.get("geo_center_lon"),
            radius_km=st.session_state.get("geo_radius_km"),
            listing_type_filter=st.session_state.get("listing_type_filter"),
            min_price=st.session_state.get("retr_min_price"),
            max_price=st.session_state.get("retr_max_price"),
            sort_by=st.session_state.get("retr_sort_by"),
            sort_ascending=st.session_state.get("retr_sort_ascending", True),
            year_built_min=st.session_state.get("retr_year_built_min"),
            year_built_max=st.session_state.get("retr_year_built_max"),
            energy_certs=st.session_state.get("retr_energy_certs"),
            must_have_parking=bool(st.session_state.get("retr_must_parking", False)),
            must_have_elevator=bool(st.session_state.get("retr_must_elevator", False)),
            reranker=reranker,
            strategy=strategy,
        )

        return svc_create_hybrid_agent_instance(
            llm=llm,
            retriever=retriever,
            verbose=True,
        )

    except Exception as e:
        st.error(f"Error creating hybrid agent: {e}")
        return None


def render_chat_tab():
    """Render chat interface tab."""
    lang = st.session_state.language

    # Check if data is loaded
    if not st.session_state.data_loaded:
        st.info(get_text("please_load_data", lang))

        # Show feature highlights
        st.subheader(get_text("features_title", lang))
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(
                f"""
            **{get_text('chat_tab_features', lang)}**
            - {get_text('chat_feature_1', lang)}
            - {get_text('chat_feature_2', lang)}
            - {get_text('chat_feature_3', lang)}
            - {get_text('chat_feature_4', lang)}
            """
            )

        with col2:
            st.markdown(
                f"""
            **{get_text('compare_tab_features', lang)}**
            - {get_text('compare_feature_1', lang)}
            - {get_text('compare_feature_2', lang)}
            - {get_text('compare_feature_3', lang)}
            - {get_text('compare_feature_4', lang)}
            """
            )

        with col3:
            st.markdown(
                f"""
            **{get_text('export_tab_features', lang)}**
            - {get_text('export_feature_1', lang)}
            - {get_text('export_feature_2', lang)}
            - {get_text('export_feature_3', lang)}
            - {get_text('export_feature_4', lang)}
            """
            )

        return

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Display source documents if available
            if message["role"] == "assistant" and "sources" in message:
                with st.expander("📚 Sources"):
                    for i, doc in enumerate(message["sources"], 1):
                        st.markdown(f"**Source {i}:**")
                        st.markdown(doc.page_content[:300] + "...")
                        st.json(doc.metadata)

    # Chat input
    if prompt := st.chat_input(get_text("chat_placeholder", lang)):
        # Track query start time (Phase 3)
        import time

        query_start = time.time()

        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Show query analysis if enabled
        if st.session_state.show_query_analysis:
            analysis = analyze_query(prompt)
            with st.expander(f"🔍 {get_text('query_analysis', lang)}", expanded=False):
                st.write(f"**{get_text('intent', lang)}:** {analysis.intent.value}")
                st.write(f"**{get_text('complexity', lang)}:** {analysis.complexity.value}")
                st.write(f"**{get_text('tools_needed', lang)}:** {[t.value for t in analysis.tools_needed]}")
                if analysis.extracted_filters:
                    st.write(f"**{get_text('extracted_filters', lang)}:** {analysis.extracted_filters}")
                st.write(f"**{get_text('should_use_agent', lang)}:** {analysis.should_use_agent()}")

        # Generate response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()

            try:
                # Use hybrid agent or regular chain based on settings
                use_hybrid = st.session_state.use_hybrid_agent

                if use_hybrid:
                    # Create or get hybrid agent
                    if st.session_state.hybrid_agent is None:
                        with st.spinner("Initializing AI agent..."):
                            st.session_state.hybrid_agent = create_hybrid_agent_instance()

                    if st.session_state.hybrid_agent is None:
                        st.error(get_text("failed_create_agent", lang))
                        return

                    # Get response from hybrid agent
                    with st.spinner("🧠 Analyzing query and processing..."):
                        response = st.session_state.hybrid_agent.process_query(
                            query=prompt, return_analysis=True
                        )

                    answer = response["answer"]
                    source_docs = response.get("source_documents", [])
                    method = response.get("method", "unknown")
                    intent = response.get("intent", "unknown")

                    # Display method badge
                    if method == "agent":
                        st.caption("🛠️ Processed with AI Agent + Tools")
                    elif method == "hybrid":
                        st.caption("🔀 Processed with Hybrid (RAG + Agent)")
                    else:
                        st.caption("📚 Processed with RAG")

                else:
                    # Use regular RAG chain
                    if st.session_state.conversation_chain is None:
                        with st.spinner("Initializing conversation..."):
                            st.session_state.conversation_chain = create_conversation_chain()

                    if st.session_state.conversation_chain is None:
                        st.error(get_text("failed_create_chain", lang))
                        return

                    # Get response
                    with st.spinner("Thinking..."):
                        response = st.session_state.conversation_chain({"question": prompt})

                    answer = response["answer"]
                    source_docs = response.get("source_documents", [])

                # Apply reranking if enabled
                if st.session_state.use_reranking and source_docs:
                    reranker = create_reranker(advanced=True)
                    reranked = reranker.rerank(
                        query=prompt, documents=source_docs, k=min(5, len(source_docs))
                    )
                    source_docs = [doc for doc, score in reranked]
                    st.caption("✨ Results reranked for relevance")

                # Display answer
                response_placeholder.markdown(answer)

                # Track query completion (Phase 3)
                processing_time_ms = int((time.time() - query_start) * 1000)
                intent_val = intent if use_hybrid else "unknown"
                st.session_state.session_tracker.track_query(
                    query=prompt,
                    intent=intent_val,
                    complexity="medium",
                    processing_time_ms=processing_time_ms,
                )

                # Save to history
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "sources": source_docs}
                )

                # Display sources
                if source_docs:
                    with st.expander(f"📚 Sources ({len(source_docs)})"):
                        for i, doc in enumerate(source_docs, 1):
                            st.markdown(f"**Source {i}:**")
                            st.markdown(doc.page_content[:300] + "...")
                            with st.container():
                                st.json(doc.metadata, expanded=False)

            except Exception as e:
                st.error(f"Error generating response: {e}")
                st.exception(e)

                # Track error (Phase 3)
                st.session_state.session_tracker.track_error(
                    error_type=type(e).__name__, error_message=str(e)
                )


def render_market_insights_tab():
    """Render market insights and analytics tab."""
    lang = st.session_state.language

    if not st.session_state.data_loaded or st.session_state.market_insights is None:
        st.info(get_text("please_load_data_insights", lang))
        return

    st.header(f"📈 {get_text('market_insights_analytics', lang)}")

    insights = st.session_state.market_insights

    # Overall statistics
    stats = insights.get_overall_statistics()

    st.subheader(get_text("market_overview", lang))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(get_text("total_properties", lang), stats.total_properties)
    with col2:
        st.metric(get_text("average_price", lang), f"${stats.average_price:.2f}")
    with col3:
        st.metric(get_text("median_price", lang), f"${stats.median_price:.2f}")
    with col4:
        st.metric(get_text("avg_rooms", lang), f"{stats.avg_rooms:.1f}")

    st.divider()

    # Price trends
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(get_text("price_trend", lang))
        trend = insights.get_price_trend()
        trend_emoji = {
            "increasing": "📈",
            "decreasing": "📉",
            "stable": "➡️",
            "insufficient_data": "❓",
        }.get(trend.direction.value, "")

        st.metric(
            get_text("market_direction", lang),
            f"{trend_emoji} {trend.direction.value.title()}",
            f"{trend.change_percent:+.1f}%",
        )
        st.caption(f"{get_text('confidence_high', lang).split(':')[0]}: {trend.confidence.title()}")
        st.caption(
            f"{get_text('sample_size', lang)}: {trend.sample_size} {get_text('properties', lang).lower()}"
        )

    with col2:
        st.subheader(get_text("price_distribution", lang))
        price_dist = insights.get_price_distribution(bins=8)
        dist_df = pd.DataFrame({"Price Range": price_dist["bins"], "Count": price_dist["counts"]})
        try:
            st.bar_chart(dist_df.set_index("Price Range"))
        except Exception:
            try:
                import matplotlib.pyplot as plt

                fig, ax = plt.subplots()
                s = dist_df.set_index("Price Range")["Count"]
                s.plot(kind="bar", ax=ax)
                ax.set_xlabel("Price Range")
                ax.set_ylabel("Count")
                st.pyplot(fig)
            except Exception:
                st.dataframe(dist_df)

    st.divider()

    # Location insights
    st.subheader(get_text("location_analysis", lang))

    cities = list(stats.cities.keys())
    if len(cities) >= 2:
        col1, col2 = st.columns(2)

        with col1:
            selected_city = st.selectbox(get_text("select_city", lang), cities)
            if selected_city:
                city_insights = insights.get_location_insights(selected_city)
                if city_insights:
                    st.write(f"**{city_insights.city}**")
                    st.write(f"{get_text('properties', lang)}: {city_insights.property_count}")
                    st.write(
                        f"{get_text('average_price', lang).split()[0]}: ${city_insights.avg_price:.2f}"
                    )
                    st.write(f"{get_text('median_price', lang)}: ${city_insights.median_price:.2f}")
                    if city_insights.avg_price_per_sqm:
                        st.write(f"Price/sqm: ${city_insights.avg_price_per_sqm:.2f}")
                    st.write(
                        f"{get_text('market_position', lang)} {city_insights.price_comparison.replace('_', ' ').title()}"
                    )

        with col2:
            if len(cities) >= 2:
                st.write(f"**{get_text('city_comparison', lang)}**")
                compare_city1 = st.selectbox(
                    get_text("compare_city_1", lang), cities, key="compare1"
                )
                compare_city2 = st.selectbox(
                    get_text("compare_city_2", lang),
                    [c for c in cities if c != compare_city1],
                    key="compare2",
                )

                if compare_city1 and compare_city2:
                    comparison = insights.compare_locations(compare_city1, compare_city2)
                    if "error" not in comparison:
                        cheaper = comparison["cheaper_city"]
                        diff = abs(comparison["price_difference"])
                        diff_pct = abs(comparison["price_difference_percent"])
                        st.write(
                            f"{cheaper} {get_text('is_cheaper_by', lang)} ${diff:,.0f} ({diff_pct:.1f}%)"
                        )

    st.divider()

    with st.expander(get_text("expert_panel", lang), expanded=False):
        cities = list(stats.cities.keys())
        colA, colB = st.columns(2)
        with colB:
            st.caption(get_text("map_filters", lang))
            map_min_price = st.number_input(
                get_text("min_price", lang),
                min_value=0.0,
                value=0.0,
                step=100.0,
                key="map_min_price_input",
            )
            map_max_price = st.number_input(
                get_text("max_price", lang),
                min_value=0.0,
                value=0.0,
                step=100.0,
                key="map_max_price_input",
            )
            map_min_ppsqm = st.number_input(
                get_text("min_price_sqm", lang),
                min_value=0.0,
                value=0.0,
                step=10.0,
                key="map_min_ppsqm_input",
            )
            map_max_ppsqm = st.number_input(
                get_text("max_price_sqm", lang),
                min_value=0.0,
                value=0.0,
                step=10.0,
                key="map_max_ppsqm_input",
            )
            rooms_min, rooms_max = st.slider(
                get_text("rooms", lang),
                min_value=0.0,
                max_value=10.0,
                value=(0.0, 10.0),
                step=1.0,
                key="map_rooms_range",
            )

            map_type_options = (
                sorted([str(x) for x in insights.df["property_type"].dropna().unique().tolist()])
                if len(insights.df) > 0
                else []
            )
            map_property_types = st.multiselect(
                get_text("property_type", lang),
                options=map_type_options,
                default=map_type_options,
                key="map_property_types",
            )

            year_series = (
                pd.to_numeric(insights.df["year_built"], errors="coerce")
                if (len(insights.df) > 0 and "year_built" in insights.df.columns)
                else pd.Series([], dtype="float")
            )
            year_values = year_series.dropna().astype(int) if len(year_series) > 0 else pd.Series([], dtype="int")
            year_bounds = (
                (int(year_values.min()), int(year_values.max())) if len(year_values) > 0 else None
            )

            if year_bounds:
                year_min, year_max = year_bounds
                y_from, y_to = st.slider(
                    get_text("year_built_range", lang),
                    min_value=year_min,
                    max_value=year_max,
                    value=(year_min, year_max),
                    step=1,
                    key="map_year_built_range",
                )
                map_year_built_min = int(y_from) if int(y_from) > year_min else None
                map_year_built_max = int(y_to) if int(y_to) < year_max else None
            else:
                map_year_built_min = None
                map_year_built_max = None
                st.caption(get_text("no_year_built_data", lang))

            energy_options = (
                sorted(
                    {
                        str(x).strip()
                        for x in insights.df["energy_cert"].dropna().tolist()
                        if str(x).strip()
                    }
                )
                if (len(insights.df) > 0 and "energy_cert" in insights.df.columns)
                else []
            )
            if energy_options:
                selected_energy_certs = st.multiselect(
                    get_text("energy_certificates", lang),
                    options=energy_options,
                    default=[],
                    key="map_energy_certs",
                )
                map_energy_certs = selected_energy_certs if selected_energy_certs else None
            else:
                map_energy_certs = None
                st.caption(get_text("no_energy_cert_data", lang))

            c1, c2 = st.columns(2)
            with c1:
                must_parking = st.checkbox(get_text("parking", lang), value=False, key="map_must_parking")
                must_elevator = st.checkbox(get_text("elevator", lang), value=False, key="map_must_elevator")
            with c2:
                must_balcony = st.checkbox(get_text("balcony", lang), value=False, key="map_must_balcony")
                must_furnished = st.checkbox(get_text("furnished", lang), value=False, key="map_must_furnished")

            map_max_points = st.slider(
                "Max Points",
                min_value=50,
                max_value=2000,
                value=500,
                step=50,
                key="map_max_points",
            )

            st.caption("City Price Indices")
            selected_cities = st.multiselect(
                "Cities", options=cities, default=cities[:3] if len(cities) >= 3 else cities
            )
            st.radio(
                "Listing Type",
                options=["Any", "Rent", "Sale"],
                horizontal=True,
                key="listing_type_filter",
            )
            st.caption("Chat Retrieval Filters")
            rc1, rc2 = st.columns(2)
            with rc1:
                retr_must_parking = st.checkbox(
                    get_text("parking", lang), value=False, key="retr_must_parking"
                )
                retr_must_elevator = st.checkbox(
                    get_text("elevator", lang), value=False, key="retr_must_elevator"
                )
            with rc2:
                pass

            if year_bounds:
                year_min, year_max = year_bounds
                ry_from, ry_to = st.slider(
                    get_text("year_built_range", lang),
                    min_value=year_min,
                    max_value=year_max,
                    value=(year_min, year_max),
                    step=1,
                    key="retr_year_built_range",
                )
                retr_year_built_min = int(ry_from) if int(ry_from) > year_min else None
                retr_year_built_max = int(ry_to) if int(ry_to) < year_max else None
            else:
                retr_year_built_min = None
                retr_year_built_max = None

            if energy_options:
                selected_retr_energy_certs = st.multiselect(
                    get_text("energy_certificates", lang),
                    options=energy_options,
                    default=[],
                    key="retr_energy_certs",
                )
                retr_energy_certs = (
                    selected_retr_energy_certs if selected_retr_energy_certs else None
                )
            else:
                retr_energy_certs = None

            min_price = st.number_input(
                "Min Price", min_value=0.0, value=0.0, step=100.0, key="retr_min_price_input"
            )
            max_price = st.number_input(
                "Max Price", min_value=0.0, value=0.0, step=100.0, key="retr_max_price_input"
            )
            sort_label = st.selectbox(
                "Sort by",
                options=["Relevance", "Price", "Price per sqm", "Rooms"],
                index=0,
                key="retr_sort_label",
            )
            sort_order = st.radio(
                "Order",
                options=["Ascending", "Descending"],
                index=0,
                horizontal=True,
                key="retr_sort_order",
            )

            pmin = float(min_price) if min_price and min_price > 0 else None
            pmax = float(max_price) if max_price and max_price > 0 else None
            if pmin is not None and pmax is not None and pmin > pmax:
                pmin, pmax = pmax, pmin
            st.session_state.retr_min_price = pmin
            st.session_state.retr_max_price = pmax
            st.session_state.retr_must_parking = bool(retr_must_parking)
            st.session_state.retr_must_elevator = bool(retr_must_elevator)
            st.session_state.retr_year_built_min = retr_year_built_min
            st.session_state.retr_year_built_max = retr_year_built_max
            st.session_state.retr_energy_certs = retr_energy_certs
            sort_by_map = {
                "Relevance": None,
                "Price": "price",
                "Price per sqm": "price_per_sqm",
                "Rooms": "rooms",
            }
            st.session_state.retr_sort_by = sort_by_map.get(sort_label)
            st.session_state.retr_sort_ascending = sort_order == "Ascending"

        with colA:
            st.caption("Map")
            if not cities:
                st.info(get_text("no_data", lang))
            else:
                center_city = st.selectbox(
                    "Center City", options=cities or [""], index=0 if cities else 0
                )
                map_mode = st.radio(
                    "Map Mode",
                    options=["Current Market", "Price Heatmap", "Historical Trends", "City Overview"],
                    horizontal=True,
                    key="map_mode_select",
                )
                radius_km = st.slider(
                    "Radius (km)", min_value=1, max_value=50, value=10, key="map_radius_km"
                )

                m_center = st.session_state.get("geo_center_lat"), st.session_state.get(
                    "geo_center_lon"
                )
                if m_center[0] is None or m_center[1] is None:
                    lat, lon = _get_city_coordinates(center_city)
                else:
                    lat, lon = float(m_center[0]), float(m_center[1])

                pmin_map = float(map_min_price) if map_min_price and map_min_price > 0 else None
                pmax_map = float(map_max_price) if map_max_price and map_max_price > 0 else None
                if pmin_map is not None and pmax_map is not None and pmin_map > pmax_map:
                    pmin_map, pmax_map = pmax_map, pmin_map

                psmin_map = float(map_min_ppsqm) if map_min_ppsqm and map_min_ppsqm > 0 else None
                psmax_map = float(map_max_ppsqm) if map_max_ppsqm and map_max_ppsqm > 0 else None
                if psmin_map is not None and psmax_map is not None and psmin_map > psmax_map:
                    psmin_map, psmax_map = psmax_map, psmin_map

                lt_label = st.session_state.get("listing_type_filter")
                listing_type = None
                if lt_label == "Rent":
                    listing_type = "rent"
                elif lt_label == "Sale":
                    listing_type = "sale"

                coords_df = (
                    insights.df.dropna(subset=["lat", "lon"])
                    if len(insights.df) > 0
                    else insights.df
                )
                excluded_no_coords = (
                    int(len(insights.df) - len(coords_df)) if len(insights.df) > 0 else 0
                )
                has_coords = len(coords_df) > 0 if len(insights.df) > 0 else False
                if not has_coords:
                    if len(insights.df) > 0:
                        st.info(f"{len(insights.df)} properties loaded, but none have coordinates.")
                    else:
                        st.info("No coordinates found in the loaded dataset.")
                    map_df = insights.df.iloc[0:0].copy()
                else:
                    if excluded_no_coords > 0:
                        st.caption(f"Excluded {excluded_no_coords} properties without coordinates.")
                    map_df = insights.filter_properties(
                        center_lat=float(lat),
                        center_lon=float(lon),
                        radius_km=float(radius_km),
                        listing_type=listing_type,
                        property_types=map_property_types,
                        min_price=pmin_map,
                        max_price=pmax_map,
                        min_price_per_sqm=psmin_map,
                        max_price_per_sqm=psmax_map,
                        min_rooms=float(rooms_min) if rooms_min > 0 else None,
                        max_rooms=float(rooms_max) if rooms_max < 10 else None,
                        must_have_parking=bool(must_parking),
                        must_have_elevator=bool(must_elevator),
                        must_have_balcony=bool(must_balcony),
                        must_be_furnished=bool(must_furnished),
                        year_built_min=map_year_built_min,
                        year_built_max=map_year_built_max,
                        energy_certs=map_energy_certs,
                        require_coords=True,
                    )

                st.write(f"Filtered properties: {len(map_df)}")
                if len(map_df) > int(map_max_points):
                    st.caption(f"Showing first {int(map_max_points)} of {len(map_df)} points.")
                st.session_state.geo_center_city = center_city
                st.session_state.geo_center_lat = float(lat)
                st.session_state.geo_center_lon = float(lon)
                st.session_state.geo_radius_km = float(radius_km)

                import folium

                if map_mode == "Historical Trends":
                    if has_coords and len(map_df) == 0:
                        st.info(get_text("no_properties_match_map_filters", lang))

                    # Convert filtered DataFrame to Property objects
                    props_list = []
                    if has_coords and len(map_df) > 0:
                        
                        for _, row in map_df.head(int(map_max_points)).iterrows():
                            try:
                                row_dict = {k: v if pd.notna(v) else None for k, v in row.items()}
                                if "lat" in row_dict:
                                    row_dict["latitude"] = row_dict.pop("lat")
                                if "lon" in row_dict:
                                    row_dict["longitude"] = row_dict.pop("lon")
                                props_list.append(Property(**row_dict))
                            except Exception:
                                continue
                    
                    hist_props = PropertyCollection(properties=props_list, total_count=len(props_list))
                    fmap = create_historical_trends_map(hist_props, center_city=center_city, zoom_start=11)
                    
                    # Add radius circle
                    folium.Circle(
                        location=[lat, lon],
                        radius=float(radius_km) * 1000.0,
                        color="#4B5563",
                        fill=True,
                        fill_opacity=0.1,
                    ).add_to(fmap)
                    
                    st_folium(fmap, height=350, use_container_width=True)
                elif map_mode == "Price Heatmap":
                    # Convert filtered DataFrame to Property objects
                    props_list = []
                    if has_coords and len(map_df) > 0:
                        for _, row in map_df.head(int(map_max_points)).iterrows():
                            try:
                                row_dict = {k: v if pd.notna(v) else None for k, v in row.items()}
                                if "lat" in row_dict:
                                    row_dict["latitude"] = row_dict.pop("lat")
                                if "lon" in row_dict:
                                    row_dict["longitude"] = row_dict.pop("lon")
                                props_list.append(Property(**row_dict))
                            except Exception:
                                continue
                    coll = PropertyCollection(properties=props_list, total_count=len(props_list))
                    fmap = create_price_heatmap(coll, center_city=center_city, zoom_start=11, radius=15, blur=25, jitter=True)
                    folium.Circle(
                        location=[lat, lon],
                        radius=float(radius_km) * 1000.0,
                        color="#4B5563",
                        fill=True,
                        fill_opacity=0.1,
                    ).add_to(fmap)
                    st_folium(fmap, height=350, use_container_width=True)
                elif map_mode == "City Overview":
                    # Convert filtered DataFrame to Property objects
                    props_list = []
                    if has_coords and len(map_df) > 0:
                        for _, row in map_df.head(int(map_max_points)).iterrows():
                            try:
                                row_dict = {k: v if pd.notna(v) else None for k, v in row.items()}
                                if "lat" in row_dict:
                                    row_dict["latitude"] = row_dict.pop("lat")
                                if "lon" in row_dict:
                                    row_dict["longitude"] = row_dict.pop("lon")
                                props_list.append(Property(**row_dict))
                            except Exception:
                                continue
                    coll = PropertyCollection(properties=props_list, total_count=len(props_list))
                    fmap = create_city_overview_map(coll, show_statistics=True)
                    st_folium(fmap, height=350, use_container_width=True)
                
                else:
                    props_list = []
                    if has_coords and len(map_df) > 0:
                        for _, row in map_df.head(int(map_max_points)).iterrows():
                            try:
                                row_dict = {k: v if pd.notna(v) else None for k, v in row.items()}
                                if "lat" in row_dict:
                                    row_dict["latitude"] = row_dict.pop("lat")
                                if "lon" in row_dict:
                                    row_dict["longitude"] = row_dict.pop("lon")
                                props_list.append(Property(**row_dict))
                            except Exception:
                                continue

                    coll = PropertyCollection(properties=props_list, total_count=len(props_list))
                    fmap = create_property_map(coll, center_city=center_city, zoom_start=11, add_clusters=True, show_legend=True, jitter=True)

                    folium.Circle(
                        location=[lat, lon],
                        radius=float(radius_km) * 1000.0,
                        color="#4B5563",
                        fill=True,
                        fill_opacity=0.2,
                    ).add_to(fmap)

                    if has_coords and len(map_df) == 0:
                        st.info("No properties match the current map filters.")

                    r = st_folium(fmap, height=350, use_container_width=True)
                    click = r.get("last_clicked")
                    if click and "lat" in click and "lng" in click:
                        st.session_state.geo_center_lat = float(click["lat"])
                        st.session_state.geo_center_lon = float(click["lng"])

        if selected_cities:
            indices_df = insights.get_city_price_indices(selected_cities)
            st.dataframe(indices_df)
        else:
            st.info(get_text("load_multiple_cities", lang))

        st.caption(get_text("monthly_price_index_yoy", lang))
        ts_city = st.selectbox(
            get_text("time_series_city", lang),
            options=cities or [""],
            index=0 if cities else 0,
            key="ts_city",
        )
        ts_window = st.slider(
            get_text("moving_average_months", lang),
            min_value=1,
            max_value=12,
            value=3,
            key="ts_window",
        )
        ts_anom = st.checkbox(get_text("highlight_anomalies_zscore", lang), value=True, key="ts_anom")
        if ts_city:
            ts_df = insights.get_monthly_price_index(
                ts_city, window=int(ts_window), detect_anomalies=bool(ts_anom)
            )
            if len(ts_df) > 0:
                # Prefer smoothed line if selected
                chart_cols = ["avg_price"]
                if "avg_price_ma" in ts_df.columns:
                    chart_cols = ["avg_price_ma"]
                chart_df = ts_df[["month"] + chart_cols].set_index("month")
                st.line_chart(chart_df)
                st.dataframe(ts_df)

        st.caption(get_text("yoy_by_city_latest", lang))
        yoy_df = insights.get_cities_yoy(selected_cities or None)
        if len(yoy_df) > 0:
            st.dataframe(yoy_df)
            top_up = yoy_df.sort_values("yoy_pct", ascending=False).head(5)
            top_down = yoy_df.sort_values("yoy_pct", ascending=True).head(5)
            st.caption(get_text("top_gainers", lang))
            st.dataframe(top_up)
            st.caption(get_text("top_decliners", lang))
            st.dataframe(top_down)

        st.divider()
        st.caption(get_text("export_indices", lang))
        export_kind = st.radio(
            get_text("dataset", lang),
            options=[get_text("city_indices", lang), get_text("monthly_index", lang)],
            horizontal=True,
        )
        export_format = st.selectbox(get_text("format", lang), options=["csv", "xlsx", "json", "md"], index=0)
        gen_digest = st.checkbox(get_text("generate_expert_digest", lang))
        digest_format = st.selectbox(get_text("digest_format", lang), options=["md", "pdf"], index=0)
        if st.button(get_text("generate_indices_export", lang)):
            exp = InsightsExporter(insights)
            try:
                if gen_digest:
                    if digest_format == "md":
                        digest_md = exp.generate_digest_markdown(selected_cities or None)
                        st.download_button(
                            label=get_text("download_expert_digest_md", lang),
                            data=digest_md,
                            file_name="expert_digest.md",
                            mime="text/markdown",
                            use_container_width=True,
                        )
                    else:
                        digest_pdf = exp.generate_digest_pdf(selected_cities or None)
                        st.download_button(
                            label=get_text("download_expert_digest_pdf", lang),
                            data=digest_pdf.getvalue(),
                            file_name="expert_digest.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                else:
                    if export_kind == get_text("city_indices", lang):
                        if export_format == "csv":
                            data = exp.export_city_indices_csv(selected_cities or None)
                            mime = "text/csv"
                            filename = "city_indices.csv"
                        elif export_format == "xlsx":
                            buf = exp.export_city_indices_excel(selected_cities or None)
                            data = buf.getvalue()
                            mime = (
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                            filename = "city_indices.xlsx"
                        elif export_format == "json":
                            data = exp.export_city_indices_json(selected_cities or None)
                            mime = "application/json"
                            filename = "city_indices.json"
                        else:
                            data = exp.export_city_indices_markdown(selected_cities or None)
                            mime = "text/markdown"
                            filename = "city_indices.md"
                    else:
                        city = ts_city if ts_city else None
                        if export_format == "csv":
                            data = exp.export_monthly_index_csv(city)
                            mime = "text/csv"
                            filename = "monthly_index.csv"
                        elif export_format == "xlsx":
                            buf = exp.export_monthly_index_excel(city)
                            data = buf.getvalue()
                            mime = (
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                            filename = "monthly_index.xlsx"
                        elif export_format == "json":
                            data = exp.export_monthly_index_json(city)
                            mime = "application/json"
                            filename = "monthly_index.json"
                        else:
                            data = exp.export_monthly_index_markdown(city)
                            mime = "text/markdown"
                            filename = "monthly_index.md"

                    st.download_button(
                        label=f"Download {export_format.upper()}",
                        data=data,
                        file_name=filename,
                        mime=mime,
                        use_container_width=True,
                    )
            except Exception as e:
                st.error(f"Failed to export indices: {e}")

    st.divider()

    # Best value properties
    st.subheader(f"🏆 {get_text('best_value_properties', lang)}")

    best_values = insights.get_best_value_properties(top_n=5)
    if best_values:
        for i, prop in enumerate(best_values, 1):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            with col1:
                st.write(f"**{i}. {prop['city']}**")
            with col2:
                st.write(f"${prop['price']:.0f}/mo")
            with col3:
                st.write(f"{int(prop['rooms'])} rooms")
            with col4:
                st.write(f"⭐ {prop['value_score']:.2f}")

    st.divider()

    # Amenity impact
    st.subheader(get_text("amenity_impact_title", lang))

    amenity_impact = insights.get_amenity_impact_on_price()
    if amenity_impact:
        impact_df = pd.DataFrame(
            [
                {"Amenity": amenity.replace("_", " ").title(), "Price Increase %": impact}
                for amenity, impact in amenity_impact.items()
            ]
        ).sort_values("Price Increase %", ascending=False)

        try:
            st.bar_chart(impact_df.set_index("Amenity"))
        except Exception:
            try:
                import matplotlib.pyplot as plt

                fig, ax = plt.subplots()
                s = impact_df.set_index("Amenity")["Price Increase %"]
                s.plot(kind="bar", ax=ax)
                ax.set_xlabel("Amenity")
                ax.set_ylabel("Price Increase %")
                st.pyplot(fig)
            except Exception:
                st.dataframe(impact_df)
        st.caption(get_text("amenity_impact_caption", lang))


def render_export_tab():
    """Render export functionality tab."""
    lang = st.session_state.language

    if not st.session_state.data_loaded or st.session_state.property_collection is None:
        st.info(get_text("please_load_data_export", lang))
        return

    st.header(f"💾 {get_text('export_properties', lang)}")

    st.write(get_text("export_subtitle", lang))

    # Export options
    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader(get_text("export_settings", lang))

        format_choice = st.selectbox(
            get_text("select_format", lang),
            options=[fmt.value for fmt in ExportFormat],
            format_func=lambda x: {
                "csv": "📄 CSV (Spreadsheet)",
                "xlsx": "📊 Excel (Multi-sheet)",
                "json": "🔧 JSON (Structured)",
                "md": "📝 Markdown (Report)",
            }.get(x, x),
        )

        include_summary = st.checkbox(get_text("include_summary_stats", lang), value=True)

        if format_choice == "md":
            max_props = st.number_input(
                get_text("max_properties_report", lang),
                min_value=5,
                max_value=len(st.session_state.property_collection.properties),
                value=min(20, len(st.session_state.property_collection.properties)),
            )

    with col2:
        st.subheader(get_text("preview", lang))

        properties = st.session_state.property_collection
        st.write(f"**{get_text('total_properties', lang)}:** {len(properties.properties)}")

        if properties.properties:
            sample = properties.properties[0]
            st.write(
                f"**{get_text('sample', lang)}** {sample.city} - ${sample.price}/mo - {int(sample.rooms)} {get_text('rooms', lang).lower()}"
            )

        st.divider()

        # Export button
        if st.button(
            get_text("generate_export_button", lang), type="primary", use_container_width=True
        ):
            try:
                with st.spinner(f"Generating {format_choice.upper()} export..."):
                    exporter = PropertyExporter(properties)

                    if format_choice == "csv":
                        data = exporter.export_to_csv()
                        filename = exporter.get_filename(ExportFormat.CSV)
                        mime = "text/csv"

                    elif format_choice == "xlsx":
                        data = exporter.export_to_excel(
                            include_summary=include_summary, include_statistics=True
                        )
                        filename = exporter.get_filename(ExportFormat.EXCEL)
                        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        data = data.getvalue()

                    elif format_choice == "json":
                        data = exporter.export_to_json(
                            pretty=True, include_metadata=include_summary
                        )
                        filename = exporter.get_filename(ExportFormat.JSON)
                        mime = "application/json"

                    else:  # markdown
                        data = exporter.export_to_markdown(
                            include_summary=include_summary,
                            max_properties=max_props if format_choice == "md" else None,
                        )
                        filename = exporter.get_filename(ExportFormat.MARKDOWN)
                        mime = "text/markdown"

                    # Track export (Phase 3)
                    st.session_state.session_tracker.track_export(
                        format=format_choice, property_count=len(properties.properties)
                    )

                    st.success("✅ Export generated successfully!")

                    st.download_button(
                        label=f"📥 Download {format_choice.upper()}",
                        data=data,
                        file_name=filename,
                        mime=mime,
                        use_container_width=True,
                    )

            except Exception as e:
                st.error(f"Error generating export: {e}")
                st.exception(e)

    st.divider()

    # Export format descriptions
    with st.expander(f"ℹ️ {get_text('format_information', lang)}"):
        st.markdown(
            """
        **CSV (Comma-Separated Values)**
        - Simple spreadsheet format
        - Compatible with Excel, Google Sheets
        - Best for data import/export

        **Excel (XLSX)**
        - Multi-sheet workbook
        - Includes summary and statistics sheets
        - Best for comprehensive reports

        **JSON (JavaScript Object Notation)**
        - Structured data format
        - Best for API integration
        - Machine-readable

        **Markdown (MD)**
        - Human-readable report format
        - Best for documentation
        - Includes summaries and descriptions
        """
        )


def render_comparisons_tab():
    """Render property comparison tab."""
    lang = st.session_state.language

    if not st.session_state.data_loaded or st.session_state.property_collection is None:
        st.info(get_text("please_load_data_compare", lang))
        return

    st.header(f"🔄 {get_text('property_comparison', lang)}")

    properties = st.session_state.property_collection.properties

    st.write(get_text("select_2_4_properties", lang))

    # Property selection
    st.subheader(get_text("select_properties", lang))

    # Create property display names
    property_options = {
        f"{i+1}. {prop.city} - ${prop.price} - {int(prop.rooms)}BR ({prop.id})": prop
        for i, prop in enumerate(properties)
    }

    selected_names = st.multiselect(
        get_text("choose_properties_2_4", lang),
        options=list(property_options.keys()),
        max_selections=4,
    )

    selected_properties = [property_options[name] for name in selected_names]

    if len(selected_properties) < 2:
        st.info(get_text("select_at_least_2", lang))
        return

    if len(selected_properties) > 4:
        st.warning(get_text("maximum_4_properties", lang))
        return

    st.divider()

    # Display comparison
    try:
        display_comparison_dashboard(selected_properties, show_export=True)

    except Exception as e:
        st.error(f"Error creating comparison: {e}")
        st.exception(e)


def render_analytics_tab():
    """Render session analytics tab."""
    lang = st.session_state.language

    st.header(f"📊 {get_text('session_analytics', lang)}")

    tracker = st.session_state.session_tracker

    # Session statistics
    stats = tracker.get_session_stats()

    st.subheader(get_text("current_session", lang))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(get_text("queries", lang), stats.total_queries)
    with col2:
        st.metric(get_text("property_views", lang), stats.total_property_views)
    with col3:
        st.metric(get_text("exports", lang), stats.total_exports)
    with col4:
        st.metric(get_text("duration", lang), f"{stats.total_duration_minutes:.1f} min")

    st.divider()

    # Popular queries
    if stats.total_queries > 0:
        st.subheader(get_text("query_activity", lang))

        popular = tracker.get_popular_queries(top_n=5)
        if popular:
            st.write("**Most Common Intents:**")
            for item in popular:
                st.write(f"- {item['intent']}: {item['count']} queries")

        # Average processing time
        avg_time = tracker.get_avg_processing_time(EventType.QUERY)
        if avg_time:
            st.metric("Avg Query Processing Time", f"{avg_time:.0f}ms")

    st.divider()

    # Models used
    if stats.unique_models_used:
        st.subheader(get_text("models_used", lang))
        for model in stats.unique_models_used:
            st.write(f"- {model}")

    # Tools used
    if stats.tools_used:
        st.subheader(get_text("tools_used", lang))
        tool_counts = {}
        for tool in stats.tools_used:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

        for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True):
            st.write(f"- {tool}: {count} times")

    st.divider()

    # Aggregate statistics
    try:
        aggregate = SessionTracker.get_aggregate_stats()
        if aggregate.get("total_sessions", 0) > 0:
            st.subheader(get_text("all_time_stats", lang))

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Sessions", aggregate.get("total_sessions", 0))
            with col2:
                st.metric("Total Queries", aggregate.get("total_queries", 0))
            with col3:
                st.metric("Total Exports", aggregate.get("total_exports", 0))

    except Exception:
        pass  # Aggregate stats not available

    st.divider()

    st.caption(f"Session ID: {st.session_state.session_id}")


def render_notifications_tab():
    """Render notifications configuration and management tab."""
    lang = st.session_state.language

    st.header(f"🔔 {get_text('notification_settings', lang)}")

    # User email input
    st.subheader(f"📧 {get_text('user_information', lang)}")
    user_email = st.text_input(
        get_text("your_email", lang),
        value=st.session_state.user_email,
        placeholder=get_text("email_placeholder", lang),
        help=get_text("email_help", lang),
    )

    if user_email != st.session_state.user_email:
        st.session_state.user_email = user_email

    st.divider()

    # Email Service Configuration
    st.subheader(f"⚙️ {get_text('email_service_config', lang)}")

    with st.expander(
        get_text("configure_email", lang), expanded=st.session_state.email_service is None
    ):
        provider_options = [
            (get_text("gmail", lang), EmailProvider.GMAIL),
            (get_text("outlook", lang), EmailProvider.OUTLOOK),
            (get_text("custom_smtp", lang), EmailProvider.CUSTOM),
        ]
        provider_by_label = dict(provider_options)

        selected_provider = st.selectbox(
            get_text("email_provider", lang),
            options=[label for label, _ in provider_options],
            help=get_text("email_provider", lang),
        )

        provider = provider_by_label[selected_provider]

        col1, col2 = st.columns(2)
        with col1:
            smtp_username = st.text_input(
                get_text("email_username", lang),
                help=get_text("email_username", lang),
                label_visibility="visible",
            )
        with col2:
            smtp_password = st.text_input(
                get_text("email_password", lang),
                type="password",
                help=get_text("app_password_help", lang),
                label_visibility="visible",
            )

        if provider == EmailProvider.CUSTOM:
            col1, col2 = st.columns(2)
            with col1:
                smtp_server = st.text_input(get_text("smtp_server", lang), value="smtp.example.com")
            with col2:
                smtp_port = st.number_input(
                    get_text("smtp_port", lang), value=587, min_value=1, max_value=65535
                )

            use_tls = st.checkbox(get_text("use_tls", lang), value=True)

        if st.button(get_text("save_email_config", lang), type="primary"):
            if not smtp_username or not smtp_password:
                st.error(get_text("provide_credentials", lang))
            else:
                try:
                    if provider == EmailProvider.GMAIL:
                        email_service = EmailServiceFactory.create_gmail_service(
                            username=smtp_username, password=smtp_password
                        )
                    elif provider == EmailProvider.OUTLOOK:
                        email_service = EmailServiceFactory.create_outlook_service(
                            username=smtp_username, password=smtp_password
                        )
                    else:  # Custom
                        config = EmailConfig(
                            provider=provider,
                            smtp_server=smtp_server,
                            smtp_port=smtp_port,
                            username=smtp_username,
                            password=smtp_password,
                            from_email=smtp_username,
                            use_tls=use_tls,
                        )
                        email_service = EmailService(config)

                    st.session_state.email_service = email_service
                    st.success(get_text("email_config_success", lang))
                except Exception:
                    st.error(get_text("email_config_error", lang))

    # Test email configuration
    if st.session_state.email_service and user_email:
        if st.button(get_text("send_test_email", lang)):
            try:
                subject, html = TestEmailTemplate.render(user_name=user_email.split("@")[0])
                success = st.session_state.email_service.send_email(
                    to_email=user_email, subject=subject, body=html, html=True
                )
                if success:
                    st.success(get_text("test_email_success", lang))
                else:
                    st.error(get_text("test_email_error", lang))
            except Exception:
                st.error(get_text("test_email_error", lang))

    st.divider()

    # Notification Preferences
    if user_email:
        st.subheader(get_text("notification_preferences", lang))

        prefs_manager = st.session_state.notification_prefs_manager
        prefs = prefs_manager.get_preferences(user_email)

        # Enable/Disable notifications
        enabled = st.checkbox(get_text("enable_notifications", lang), value=prefs.enabled)

        col1, col2 = st.columns(2)

        with col1:
            # Alert frequency
            frequency_options = {
                get_text("instant", lang): AlertFrequency.INSTANT,
                get_text("hourly", lang): AlertFrequency.HOURLY,
                get_text("daily_digest", lang): AlertFrequency.DAILY,
                get_text("weekly_digest", lang): AlertFrequency.WEEKLY,
            }

            current_freq = next(
                k for k, v in frequency_options.items() if v == prefs.alert_frequency
            )

            selected_frequency = st.selectbox(
                get_text("alert_frequency", lang),
                options=list(frequency_options.keys()),
                index=list(frequency_options.keys()).index(current_freq),
                help=get_text("frequency_help", lang),
            )

            # Price drop threshold
            price_threshold = st.slider(
                get_text("price_drop_threshold", lang),
                min_value=1.0,
                max_value=20.0,
                value=prefs.price_drop_threshold,
                step=0.5,
                help=get_text("threshold_help", lang),
            )

            # Max alerts per day
            max_alerts = st.number_input(
                get_text("max_alerts_per_day", lang),
                min_value=1,
                max_value=100,
                value=prefs.max_alerts_per_day,
                help=get_text("alerts_limit_help", lang),
            )

        with col2:
            # Quiet hours
            st.write(
                f"**{get_text('quiet_hours', lang)}** ({get_text('quiet_hours_desc', lang)})"
            )
            quiet_start = st.time_input(
                get_text("quiet_hours_start", lang),
                value=datetime.strptime(prefs.quiet_hours_start or "22:00", "%H:%M").time(),
            )
            quiet_end = st.time_input(
                get_text("quiet_hours_end", lang),
                value=datetime.strptime(prefs.quiet_hours_end or "08:00", "%H:%M").time(),
            )

            # Digest time (if daily/weekly)
            if frequency_options[selected_frequency] in [
                AlertFrequency.DAILY,
                AlertFrequency.WEEKLY,
            ]:
                digest_time = st.time_input(
                    get_text("digest_send_time", lang),
                    value=datetime.strptime(prefs.daily_digest_time, "%H:%M").time(),
                )

                if frequency_options[selected_frequency] == AlertFrequency.WEEKLY:
                    day_options = [(get_text(day.value, lang), day) for day in DigestDay]
                    day_by_label = dict(day_options)
                    digest_day = st.selectbox(
                        get_text("weekly_digest_day", lang),
                        options=[label for label, _ in day_options],
                        index=[day.value for day in DigestDay].index(prefs.weekly_digest_day.value),
                    )

        # Alert type toggles
        st.write(f"**{get_text('alert_types', lang)}**")
        alert_col1, alert_col2 = st.columns(2)

        with alert_col1:
            enable_price_drops = st.checkbox(
                get_text("price_drop_alerts", lang),
                value="price_drop" in [a.value for a in prefs.enabled_alerts],
                help=get_text("price_drop_help", lang),
            )
            enable_new_properties = st.checkbox(
                get_text("new_property_alerts", lang),
                value="new_property" in [a.value for a in prefs.enabled_alerts],
                help=get_text("new_property_help", lang),
            )

        with alert_col2:
            enable_saved_searches = st.checkbox(
                get_text("saved_search_matches", lang),
                value="saved_search_match" in [a.value for a in prefs.enabled_alerts],
                help=get_text("saved_search_help", lang),
            )
            enable_market_updates = st.checkbox(
                get_text("market_updates", lang),
                value="market_update" in [a.value for a in prefs.enabled_alerts],
                help=get_text("market_updates_help", lang),
            )

        # Save preferences button
        if st.button(get_text("save_preferences", lang), type="primary"):
            try:
                from notifications.notification_preferences import AlertType as PrefAlertType

                # Build enabled alerts set
                enabled_alerts = set()
                if enable_price_drops:
                    enabled_alerts.add(PrefAlertType.PRICE_DROP)
                if enable_new_properties:
                    enabled_alerts.add(PrefAlertType.NEW_PROPERTY)
                if enable_saved_searches:
                    enabled_alerts.add(PrefAlertType.SAVED_SEARCH_MATCH)
                if enable_market_updates:
                    enabled_alerts.add(PrefAlertType.MARKET_UPDATE)

                # Update preferences
                prefs_manager.update_preferences(
                    user_email,
                    enabled=enabled,
                    alert_frequency=frequency_options[selected_frequency],
                    price_drop_threshold=price_threshold,
                    max_alerts_per_day=max_alerts,
                    quiet_hours_start=quiet_start.strftime("%H:%M"),
                    quiet_hours_end=quiet_end.strftime("%H:%M"),
                    enabled_alerts=enabled_alerts,
                )

                if frequency_options[selected_frequency] in [
                    AlertFrequency.DAILY,
                    AlertFrequency.WEEKLY,
                ]:
                    prefs_manager.update_preferences(
                        user_email, daily_digest_time=digest_time.strftime("%H:%M")
                    )

                if frequency_options[selected_frequency] == AlertFrequency.WEEKLY:
                    prefs_manager.update_preferences(
                        user_email, weekly_digest_day=day_by_label[digest_day]
                    )

                st.success(get_text("preferences_saved", lang))
            except Exception:
                st.error(get_text("preferences_error", lang))

    st.divider()

    # Notification History
    if user_email:
        st.subheader(f"📊 {get_text('notification_history', lang)}")

        history = st.session_state.notification_history
        user_notifications = history.get_user_notifications(user_email, limit=20)

        if user_notifications:
            st.write(f"**{get_text('recent_notifications', lang)}** ({get_text('last_20', lang)})")

            for notification in user_notifications:
                with st.expander(
                    f"{notification.subject} - {notification.status.value.title()} ({notification.created_at.strftime('%Y-%m-%d %H:%M')})"
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(
                            f"**{get_text('notification_type', lang)}:** {notification.notification_type.value}"
                        )
                        st.write(f"**{get_text('status', lang)}:** {notification.status.value}")
                    with col2:
                        if notification.sent_at:
                            st.write(
                                f"**{get_text('sent', lang)}:** {notification.sent_at.strftime('%Y-%m-%d %H:%M')}"
                            )
                        if notification.delivered_at:
                            st.write(
                                f"**{get_text('delivered', lang)}:** {notification.delivered_at.strftime('%Y-%m-%d %H:%M')}"
                            )

                    if notification.error_message:
                        st.error(f"{get_text('error', lang)}: {notification.error_message}")

            # Statistics
            stats = history.get_user_statistics(user_email)

            st.divider()
            st.write(f"**{get_text('notification_stats', lang)}**")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(get_text("total_sent", lang), stats["total_sent"])
            with col2:
                st.metric(get_text("delivered", lang), stats["total_delivered"])
            with col3:
                st.metric(get_text("delivery_rate", lang), f"{stats['delivery_rate']:.1f}%")
            with col4:
                st.metric(get_text("failed", lang), stats["total_failed"])
        else:
            st.info(get_text("no_notifications_yet", lang))


def render_main_content():
    """Render main content area with tabs."""
    lang = st.session_state.language
    st.title(f"{settings.app_icon} {get_text('app_title', lang)}")
    st.caption(get_text("app_subtitle", lang))

    # Create tabs
    tab_titles = [
        get_text("tab_chat", lang),
        get_text("tab_insights", lang),
        get_text("tab_compare", lang),
        get_text("tab_export", lang),
        get_text("tab_analytics", lang),
        get_text("tab_notifications", lang),
    ]

    if st.session_state.get("developer_mode", False):
        tab_titles.append(get_text("tab_dev_dashboard", lang))

    tabs = st.tabs(tab_titles)

    with tabs[0]:
        render_chat_tab()

    with tabs[1]:
        render_market_insights_tab()

    with tabs[2]:
        render_comparisons_tab()

    with tabs[3]:
        render_export_tab()

    with tabs[4]:
        render_analytics_tab()

    with tabs[5]:
        render_notifications_tab()
    
    if st.session_state.get("developer_mode", False) and len(tabs) > 6:
        with tabs[6]:
            render_dev_dashboard()


def apply_theme():
    """Apply custom CSS for light theme only."""
    theme = "light"

    if theme == "dark":
        st.markdown(
            """
        <style>
            /* Dark theme colors - Comprehensive */
            .stApp {
                background-color: #0e1117 !important;
                color: #fafafa !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif !important;
            }
            .stSidebar {
                background-color: #1a1d24 !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif !important;
            }
            /* BaseWeb token overrides for dark palette */
            [data-baseweb] {
                --colorsBackgroundPrimary: #0f172a !important;
                --colorsBackgroundSecondary: #111827 !important;
                --colorsBackgroundTertiary: #1f2937 !important;
                --colorsContentPrimary: #f9fafb !important;
                --colorsContentSecondary: #e5e7eb !important;
                --colorsContentInversePrimary: #f9fafb !important;
                --colorsBorderOpaque: #374151 !important;
                --colorsButtonPrimaryFill: #1f2937 !important;
                --colorsButtonPrimaryText: #e5e7eb !important;
            }
            /* Form inputs - dark */
            .stTextInput>div>div>input, .stSelectbox>div>div>div,
            .stTextArea>div>div>textarea, .stNumberInput>div>div>input {
                background-color: #0f172a !important;
                color: #f9fafb !important;
                border-color: #374151 !important;
            }
            .stTextInput>div>div,
            .stSelectbox>div>div,
            .stTextArea>div>div,
            .stNumberInput>div>div {
                background-color: #0f172a !important;
                border-color: #374151 !important;
            }
            /* Checkbox & radio - dark */
            .stCheckbox div[role="checkbox"], div[data-baseweb="checkbox"] div:first-child {
                background-color: #0f172a !important;
                border: 1px solid #374151 !important;
            }
            .stCheckbox div[role="checkbox"][aria-checked="true"],
            div[data-baseweb="checkbox"][aria-checked="true"] div:first-child {
                background-color: #1f2937 !important;
                border-color: #60a5fa !important;
            }
            div[data-baseweb="checkbox"] svg rect { fill: #0f172a !important; stroke: #374151 !important; }
            div[data-baseweb="checkbox"][aria-checked="true"] svg rect { fill: #60a5fa !important; stroke: #60a5fa !important; }
            .stRadio div[role="radiogroup"] div[data-baseweb="radio"] div:first-child { background-color: #0f172a !important; border: 1px solid #374151 !important; }
            .stRadio div[role="radiogroup"] div[data-baseweb="radio"][aria-checked="true"] div:first-child { background-color: #1f2937 !important; border-color: #60a5fa !important; }
            div[data-baseweb="radio"] svg circle { fill: #0f172a !important; stroke: #374151 !important; }
            div[data-baseweb="radio"][aria-checked="true"] svg circle { fill: #60a5fa !important; stroke: #60a5fa !important; }
            /* Select popover/list - dark */
            div[data-baseweb="popover"], div[data-baseweb="menu"], [role="listbox"], div[data-baseweb="select"] div[role="listbox"] {
                background-color: #0f172a !important;
                color: #f9fafb !important;
                border: 1px solid #374151 !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
            }
            /* File uploader dropzone - dark */
            [data-testid="stFileUploadDropzone"] {
                background-color: #0f172a !important;
                border: 1px solid #374151 !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
            }
            [data-testid="stFileUploadDropzone"] * { color: #f9fafb !important; }
            [data-testid="stFileUploadDropzone"] button { background-color: #1f2937 !important; color: #e5e7eb !important; border: 1px solid #374151 !important; }
            /* Toolbar menu - dark */
            [data-testid="stToolbar"] [data-baseweb="popover"], [data-testid="stToolbar"] [data-baseweb="menu"] {
                background-color: #0f172a !important;
                color: #f9fafb !important;
                border: 1px solid #374151 !important;
                box-shadow: 0 8px 24px rgba(0,0,0,0.35) !important;
            }
            /* Prevent stray scrollbars/columns */
            [data-testid="stSidebar"] { overflow-y: auto !important; }
            [data-testid="stAppViewContainer"] { overflow-x: hidden !important; }
            /* Sidebar text elements */
            .stSidebar .stMarkdown, .stSidebar h1, .stSidebar h2, .stSidebar h3,
            .stSidebar p, .stSidebar span, .stSidebar label, .stSidebar .stCaption {
                color: #fafafa !important;
            }
            /* Tabs */
            .stTabs [data-baseweb="tab-list"] {
                gap: 8px;
                background-color: #1a1d24 !important;
            }
            .stTabs [data-baseweb="tab"] {
                background-color: #262730 !important;
                color: #fafafa !important;
                border-radius: 4px 4px 0px 0px;
            }
            .stTabs [aria-selected="true"] {
                background-color: #3a3f4b !important;
                color: #fafafa !important;
            }
            /* Form inputs */
            .stTextInput>div>div>input, .stSelectbox>div>div>div,
            .stTextArea>div>div>textarea, .stNumberInput>div>div>input {
                background-color: #262730 !important;
                color: #fafafa !important;
                border-color: #3a3f4b !important;
            }
            /* Buttons */
            .stButton>button {
                background-color: #262730 !important;
                color: #fafafa !important;
                border: 1px solid #3a3f4b !important;
            }
            .stButton>button:hover {
                background-color: #3a3f4b !important;
                border: 1px solid #4a4f5b !important;
            }
            /* All text elements */
            .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown li {
                color: #fafafa !important;
            }
            /* Chat messages */
            .stChatMessage {
                background-color: #1a1d24 !important;
                color: #fafafa !important;
            }
            /* Metrics - comprehensive visibility */
            div[data-testid="stMetric"] {
                background-color: #1a1d24 !important;
            }
            div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"],
            div[data-testid="stMetricDelta"], [data-testid="stMetric"] label,
            [data-testid="stMetric"] p, [data-testid="stMetric"] span,
            [data-testid="stMetric"] div {
                color: #fafafa !important;
            }
            /* Expanders */
            .stExpander {
                background-color: #262730 !important;
                border-color: #3a3f4b !important;
            }
            .stExpander p, .stExpander span, .stExpander label {
                color: #fafafa !important;
            }
            /* Headers */
            h1, h2, h3, h4, h5, h6 {
                color: #fafafa !important;
            }
            /* Form controls */
            .stRadio label, .stCheckbox label {
                color: #fafafa !important;
            }
            .stSlider label, .stSlider p {
                color: #fafafa !important;
            }
            /* Header bar */
            [data-testid="stHeader"] {
                background-color: #0e1117 !important;
            }
            /* Captions */
            .stCaption {
                color: #b0b0b0 !important;
            }
            /* Alerts */
            .stAlert {
                background-color: #262730 !important;
                color: #fafafa !important;
            }
            /* Dataframes */
            .stDataFrame {
                color: #fafafa !important;
            }
            /* Multiselect */
            .stMultiSelect label {
                color: #fafafa !important;
            }
        </style>
        """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
        <script>
        try {
          localStorage.setItem('ai-real-estate-theme','dark');
          document.documentElement.setAttribute('data-theme','dark');
          document.body.setAttribute('data-theme','dark');
          var stApp = document.querySelector('.stApp'); if (stApp) stApp.setAttribute('data-theme','dark');
        } catch(e) {}
        </script>
        """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
        <script>
        setTimeout(() => {
          document.querySelectorAll('input').forEach(el => {
            const label = (el.getAttribute('aria-label') || '').toLowerCase();
            if (label.includes('api key') || label.includes('password')) {
              el.setAttribute('autocomplete','off');
              el.setAttribute('autocapitalize','off');
              el.setAttribute('spellcheck','false');
            }
          });
        }, 0);
        </script>
        """,
            unsafe_allow_html=True,
        )
    else:
        # Light theme (default Streamlit theme)
        st.markdown(
            """
        <style>
            /* Light theme colors (enhanced) */
            .stApp {
                background-color: #ffffff;
                color: #31333F;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif !important;
            }
            /* BaseWeb token overrides to enforce light palette */
            [data-baseweb] {
                --colorsBackgroundPrimary: #ffffff !important;
                --colorsBackgroundSecondary: #f8fafc !important;
                --colorsBackgroundTertiary: #eef2f7 !important;
                --colorsContentPrimary: #1f2937 !important;
                --colorsContentSecondary: #31333F !important;
                --colorsContentInversePrimary: #31333F !important;
                --colorsBorderOpaque: #d1d5db !important;
                --colorsButtonPrimaryFill: #e2e8f0 !important;
                --colorsButtonPrimaryText: #1f2937 !important;
            }
            .stSidebar {
                background-color: #f0f2f6;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif !important;
            }
            /* Prevent stray scrollbars/columns */
            [data-testid="stSidebar"] { overflow-y: auto !important; }
            [data-testid="stAppViewContainer"] { overflow-x: hidden !important; }
            /* Sidebar text elements */
            .stSidebar .stMarkdown, .stSidebar h1, .stSidebar h2, .stSidebar h3,
            .stSidebar p, .stSidebar span, .stSidebar label, .stSidebar .stCaption {
                color: #31333F !important;
            }
            /* Tabs */
            .stTabs [data-baseweb="tab-list"] {
                gap: 8px;
                background-color: #f0f2f6 !important;
            }
            .stTabs [data-baseweb="tab"] {
                background-color: #eef2f7 !important;
                color: #31333F !important;
                border-radius: 4px 4px 0px 0px;
            }
            .stTabs [aria-selected="true"] {
                background-color: #e2e8f0 !important;
                color: #31333F !important;
            }
            /* Form inputs */
            .stTextInput>div>div>input, .stSelectbox>div>div>div,
            .stTextArea>div>div>textarea, .stNumberInput>div>div>input {
                background-color: #ffffff !important;
                color: #31333F !important;
                border-color: #d1d5db !important;
            }
            .stTextInput>div>div,
            .stSelectbox>div>div,
            .stTextArea>div>div,
            .stNumberInput>div>div {
                background-color: #ffffff !important;
                border-color: #d1d5db !important;
            }
            .stTextInput>div>div,
            .stSelectbox>div>div,
            .stTextArea>div>div,
            .stNumberInput>div>div {
                border-radius: 0.375rem !important;
            }
            /* Password visibility toggle */
            .stTextInput button[aria-label*="password"],
            .stTextInput button[aria-label*="Password"],
            .stTextInput button[aria-label*="Show"],
            .stTextInput button[aria-label*="Hide"] {
                background-color: #ffffff !important;
                color: #31333F !important;
                border: 1px solid #d1d5db !important;
            }
            .stTextInput button[aria-label*="password"] svg path,
            .stTextInput button[aria-label*="Password"] svg path,
            .stTextInput button[aria-label*="Show"] svg path,
            .stTextInput button[aria-label*="Hide"] svg path {
                fill: #31333F !important;
            }
            /* Select popover/list */
            div[data-baseweb="popover"],
            div[data-baseweb="menu"],
            [role="listbox"],
            div[data-baseweb="select"] div[role="listbox"] {
                background-color: #ffffff !important;
                color: #31333F !important;
                border: 1px solid #e5e7eb !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
            }
            /* Streamlit virtualized dropdown */
            ul[data-testid="stVirtualDropdown"] {
                background-color: #ffffff !important;
                color: #31333F !important;
                border: 1px solid #e5e7eb !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
            }
            ul[data-testid="stVirtualDropdown"] li[role="option"] {
                background-color: #ffffff !important;
                color: #31333F !important;
            }
            ul[data-testid="stVirtualDropdown"] li[role="option"][aria-selected="true"] {
                background-color: #2563eb !important;
                color: #ffffff !important;
            }
            ul[data-testid="stVirtualDropdown"] li[role="option"]:hover {
                background-color: #f1f5f9 !important;
                color: #1f2937 !important;
            }
            [role="listbox"] [role="option"],
            div[data-baseweb="menu"] li,
            .stSelectbox [role="option"],
            .stSelectbox li {
                color: #31333F !important;
                background-color: #ffffff !important;
            }
            [role="listbox"] [aria-selected="true"],
            div[data-baseweb="menu"] li[aria-selected="true"],
            .stSelectbox [role="option"][aria-selected="true"] {
                background-color: #2563eb !important;
                color: #ffffff !important;
            }
            [role="listbox"] [role="option"]:hover,
            div[data-baseweb="menu"] li:hover,
            .stSelectbox [role="option"]:hover {
                background-color: #f1f5f9 !important;
                color: #1f2937 !important;
            }
            /* Select trigger */
            .stSelectbox div[role="button"],
            div[data-baseweb="select"] div[role="button"] {
                background-color: #ffffff !important;
                color: #31333F !important;
                border-color: #d1d5db !important;
            }
            div[data-baseweb="popover"] *, div[data-baseweb="menu"] * {
                background-color: #ffffff !important;
                color: #31333F !important;
            }
            div[data-baseweb="input"] div[data-baseweb="input-enhancer"] {
                background-color: #ffffff !important;
                border-left: 1px solid #d1d5db !important;
            }
            .stSelectbox svg,
            div[data-baseweb="select"] svg {
                color: #31333F !important;
                fill: #31333F !important;
            }
            /* Buttons */
            .stButton>button {
                background-color: #eef2f7 !important;
                color: #31333F !important;
                border: 1px solid #d1d5db !important;
            }
            .stButton>button:hover {
                background-color: #e2e8f0 !important;
                border: 1px solid #cbd5e1 !important;
            }
            /* Number input stepper buttons */
            .stNumberInput button {
                background-color: #f8fafc !important;
                color: #31333F !important;
                border: 1px solid #d1d5db !important;
            }
            .stNumberInput button:hover {
                background-color: #e2e8f0 !important;
                border-color: #cbd5e1 !important;
            }
            .stNumberInput button svg path {
                fill: #31333F !important;
            }
            .stNumberInput>div>div {
                background-color: #ffffff !important;
                border-color: #d1d5db !important;
            }
            /* All text elements */
            .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown li {
                color: #31333F !important;
            }
            /* Chat messages */
            .stChatMessage {
                background-color: #f8fafc !important;
                color: #31333F !important;
            }
            /* Metrics */
            div[data-testid="stMetric"] {
                background-color: #f8fafc !important;
            }
            div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"],
            div[data-testid="stMetricDelta"], [data-testid="stMetric"] label,
            [data-testid="stMetric"] p, [data-testid="stMetric"] span,
            [data-testid="stMetric"] div {
                color: #31333F !important;
            }
            /* Expanders */
            .stExpander {
                background-color: #f8fafc !important;
                border-color: #e5e7eb !important;
            }
            .stExpander p, .stExpander span, .stExpander label {
                color: #31333F !important;
            }
            /* Headers */
            h1, h2, h3, h4, h5, h6 {
                color: #1f2937 !important;
            }
            /* Form controls */
            .stRadio label, .stCheckbox label {
                color: #31333F !important;
            }
            .stTextInput, .stSelectbox, .stTextArea, .stNumberInput, .stMultiSelect, .stSlider, .stCheckbox, .stRadio, .stButton { margin-bottom: 0.75rem !important; }
            .stExpander { margin-bottom: 0.75rem !important; }
            div[data-testid="stMetric"] { margin-bottom: 0.75rem !important; }
            .stDataFrame { margin-bottom: 0.75rem !important; }
            [data-testid="stFileUploadDropzone"] { margin-bottom: 0.75rem !important; }
            .stTabs [data-baseweb="tab-panel"] { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; }
            /* Checkbox visual */
            .stCheckbox div[role="checkbox"] {
                background-color: #ffffff !important;
                border: 1px solid #d1d5db !important;
            }
            .stCheckbox div[role="checkbox"][aria-checked="true"] {
                background-color: #e2e8f0 !important;
                border-color: #cbd5e1 !important;
            }
            .stCheckbox div[role="checkbox"] svg path {
                fill: #31333F !important;
            }
            .stSlider label, .stSlider p {
                color: #31333F !important;
            }
            .stCheckbox div[role="checkbox"],
            div[data-baseweb="checkbox"] div:first-child {
                background-color: #ffffff !important;
                border: 1px solid #d1d5db !important;
            }
            .stCheckbox div[role="checkbox"][aria-checked="true"],
            div[data-baseweb="checkbox"][aria-checked="true"] div:first-child {
                background-color: #e2e8f0 !important;
                border-color: #cbd5e1 !important;
            }
            .stCheckbox div[role="checkbox"] svg path,
            div[data-baseweb="checkbox"] svg path {
                fill: #31333F !important;
            }
            /* Strong checkbox override on container */
            div[data-baseweb="checkbox"] {
                background-color: #ffffff !important;
                border: 1px solid #d1d5db !important;
            }
            div[data-baseweb="checkbox"][aria-checked="true"] {
                background-color: #e2e8f0 !important;
                border-color: #60a5fa !important;
            }
            div[data-baseweb="checkbox"] svg,
            div[data-baseweb="checkbox"] svg path {
                color: #31333F !important;
                fill: #31333F !important;
            }
            /* Strong radio override */
            div[data-baseweb="radio"] {
                background-color: #ffffff !important;
                border: 1px solid #d1d5db !important;
            }
            div[data-baseweb="radio"][aria-checked="true"] {
                background-color: #e2e8f0 !important;
                border-color: #60a5fa !important;
            }
            div[data-baseweb="radio"] svg,
            div[data-baseweb="radio"] svg path,
            div[data-baseweb="radio"][aria-checked="true"] svg path {
                color: #31333F !important;
                fill: #31333F !important;
            }
            /* Increase specificity using emotion class pattern */
            [class*="st-emotion-cache"][data-baseweb="checkbox"],
            [class*="st-emotion-cache"][data-baseweb="radio"] {
                background-color: #ffffff !important;
                border: 1px solid #d1d5db !important;
            }
            /* BaseWeb checkbox/radio SVG fallback */
            div[data-baseweb="checkbox"] svg rect {
                fill: #ffffff !important;
                stroke: #d1d5db !important;
            }
            div[data-baseweb="checkbox"][aria-checked="true"] svg rect {
                fill: #e2e8f0 !important;
                stroke: #60a5fa !important;
            }
            div[data-baseweb="radio"] svg circle {
                fill: #ffffff !important;
                stroke: #d1d5db !important;
            }
            div[data-baseweb="radio"][aria-checked="true"] svg circle {
                fill: #60a5fa !important;
                stroke: #60a5fa !important;
            }
            /* Radio visual */
            .stRadio div[role="radiogroup"] div[data-baseweb="radio"] div:first-child {
                background-color: #ffffff !important;
                border: 1px solid #d1d5db !important;
            }
            .stRadio div[role="radiogroup"] div[data-baseweb="radio"][aria-checked="true"] div:first-child {
                background-color: #e2e8f0 !important;
                border-color: #60a5fa !important; /* blue accent for selected */
            }
            .stTabs [data-baseweb="tab-list"]::after,
            .stTabs [data-baseweb="tab-list"]::before {
                background: none !important;
            }
            div[data-baseweb="tooltip"], div[data-baseweb="tooltip"] * {
                background-color: #ffffff !important;
                color: #31333F !important;
            }
            #root > div:nth-child(1) > div.withScreencast > div > div > div > section.st-emotion-cache-1dwdiz2.eczjsme18 > div.st-emotion-cache-6qob1r.eczjsme11 > div.st-emotion-cache-1gwvy71.eczjsme12 > div > div > div > div > div:nth-child(12) {
                background-color: #ffffff !important;
                color: #31333F !important;
                border-color: #d1d5db !important;
            }
            /* File uploader dropzone (strong override) */
            [data-testid="stFileUploadDropzone"] {
                background-color: #ffffff !important;
                border: 1px solid #d1d5db !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.06) !important;
            }
            [data-testid="stFileUploadDropzone"] * {
                color: #31333F !important;
            }
            [data-testid="stFileUploadDropzone"] [data-testid="stFileUploadBrowseButton"],
            [data-testid="stFileUploadDropzone"] button {
                background-color: #eef2f7 !important;
                color: #31333F !important;
                border: 1px solid #d1d5db !important;
            }
            /* BaseWeb dropzone containers */
            div[data-baseweb="file-uploader"], div[data-baseweb="dropzone"],
            div[data-baseweb="file-uploader"] *, div[data-baseweb="dropzone"] * {
                background-color: #ffffff !important;
                color: #31333F !important;
            }
            /* Header bar */
            [data-testid="stHeader"] {
                background-color: #ffffff !important;
            }
            [data-testid="stToolbar"], [data-testid="stTopLeftToolBar"] {
                background-color: #ffffff !important;
                color: #31333F !important;
            }
            [data-testid="stToolbar"] svg path,
            [data-testid="stToolbar"] svg,
            [data-testid="stToolbar"] button {
                color: #31333F !important;
                fill: #31333F !important;
            }
            [data-testid="stToolbar"] [data-baseweb="popover"],
            [data-testid="stToolbar"] [data-baseweb="menu"] {
                background-color: #ffffff !important;
                color: #0f172a !important;
                border: 1px solid #e5e7eb !important;
                box-shadow: 0 8px 24px rgba(0,0,0,0.08) !important;
            }
            [data-testid="stToolbar"] [data-baseweb="menu"] li {
                padding: 10px 14px !important;
                color: #0f172a !important;
                border-bottom: 1px solid #e5e7eb !important;
            }
            [data-testid="stToolbar"] [data-baseweb="menu"] li:hover {
                background-color: #f1f5f9 !important;
            }
            [data-testid="stToolbar"] [data-baseweb="menu"] li:focus,
            [data-testid="stToolbar"] [data-baseweb="menu"] li:focus-visible {
                outline: none !important;
                box-shadow: none !important;
                background-color: #e2e8f0 !important;
            }
            div[data-baseweb="modal"],
            div[data-baseweb="modal"] *,
            div[data-baseweb="drawer"],
            div[data-baseweb="drawer"] * {
                background-color: #ffffff !important;
                color: #31333F !important;
                border-color: #e5e7eb !important;
            }
            div[data-baseweb="modal"] [data-baseweb="select"] [role="listbox"],
            div[data-baseweb="drawer"] [data-baseweb="select"] [role="listbox"] {
                background-color: #ffffff !important;
                color: #31333F !important;
                border: 1px solid #e5e7eb !important;
            }
            div[data-baseweb="modal"] [data-baseweb="button"] > button,
            div[data-baseweb="drawer"] [data-baseweb="button"] > button {
                background-color: #eef2f7 !important;
                color: #31333F !important;
                border: 1px solid #d1d5db !important;
            }
            div[data-baseweb="modal"] [data-baseweb="button"] > button:hover,
            div[data-baseweb="drawer"] [data-baseweb="button"] > button:hover {
                background-color: #e2e8f0 !important;
                border-color: #cbd5e1 !important;
            }
            div[data-baseweb="modal"] h1,
            div[data-baseweb="modal"] h2,
            div[data-baseweb="modal"] h3,
            div[data-baseweb="modal"] h4,
            div[data-baseweb="modal"] h5,
            div[data-baseweb="modal"] h6 {
                color: #1f2937 !important;
            }
            div[data-baseweb="modal"] label,
            div[data-baseweb="drawer"] label {
                color: #31333F !important;
            }
            div[data-baseweb="modal"] [data-baseweb="checkbox"] {
                background-color: #ffffff !important;
                border: 1px solid #d1d5db !important;
            }
            div[data-baseweb="modal"] [data-baseweb="checkbox"][aria-checked="true"] {
                background-color: #e2e8f0 !important;
                border-color: #60a5fa !important;
            }
            div[data-baseweb="modal"] [data-baseweb="radio"] {
                background-color: #ffffff !important;
                border: 1px solid #d1d5db !important;
            }
            div[data-baseweb="modal"] [data-baseweb="radio"][aria-checked="true"] {
                background-color: #e2e8f0 !important;
                border-color: #60a5fa !important;
            }
            div[data-baseweb="modal"] [data-baseweb="checkbox"] svg rect,
            div[data-baseweb="modal"] [data-baseweb="radio"] svg circle {
                color: #31333F !important;
                fill: #31333F !important;
                stroke: #d1d5db !important;
            }
            div[data-baseweb="modal"] [data-baseweb="select"] div[role="button"] {
                background-color: #ffffff !important;
                color: #31333F !important;
                border-color: #d1d5db !important;
            }
            /* Captions */
            .stCaption {
                color: #64748b !important;
            }
            /* Alerts */
            .stAlert {
                background-color: #eef2f7 !important;
                color: #31333F !important;
            }
            /* Dataframes */
            .stDataFrame {
                color: #31333F !important;
            }
            /* Multiselect */
            .stMultiSelect label {
                color: #31333F !important;
            }
        </style>
        """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
        <script>
        try {
          localStorage.setItem('ai-real-estate-theme','light');
          document.documentElement.setAttribute('data-theme','light');
          document.body.setAttribute('data-theme','light');
          var stApp = document.querySelector('.stApp'); if (stApp) stApp.setAttribute('data-theme','light');
        } catch(e) {}
        </script>
        """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
        <script>
        (function(){
          function markReadonly(){
            document.querySelectorAll('div[data-baseweb="select"] input').forEach(function(inp){
              try { inp.setAttribute('readonly','readonly'); inp.style.caretColor='transparent'; inp.style.userSelect='none'; } catch(_) {}
            });
          }
          document.addEventListener('keydown', function(e){
            const t = e.target;
            if (t && t.tagName === 'INPUT' && t.closest('div[data-baseweb="select"]')) {
              const allowed = ['Tab','Enter','Escape','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Home','End','PageUp','PageDown'];
              if (allowed.indexOf(e.key) === -1 && e.key && e.key.length === 1) { e.preventDefault(); }
            }
          }, true);
          document.addEventListener('input', function(e){
            const t = e.target;
            if (t && t.tagName === 'INPUT' && t.closest('div[data-baseweb="select"]')) { try { t.value=''; } catch(_) {} }
          }, true);
          document.addEventListener('beforeinput', function(e){
            const t = e.target;
            if (t && t.tagName === 'INPUT' && t.closest('div[data-baseweb="select"]')) {
              if (e.data && e.data.length > 0) { try { e.preventDefault(); } catch(_) {} }
            }
          }, true);
          document.addEventListener('focusin', function(e){
            const t = e.target;
            if (t && t.tagName === 'INPUT' && t.closest('div[data-baseweb="select"]')) { try { t.blur(); } catch(_) {} }
          }, true);
          const observer = new MutationObserver(function(){ markReadonly(); });
          observer.observe(document.body, {childList:true, subtree:true});
          markReadonly();
          setInterval(markReadonly, 500);
        })();
        </script>
        """,
            unsafe_allow_html=True,
        )


def main():
    """Main application entry point."""
    # Initialize session state
    initialize_session_state()

    # Apply theme
    apply_theme()

    # Styles already injected globally to ensure consistency

    # Render UI
    render_sidebar()
    render_main_content()

    # Footer
    lang = st.session_state.language
    st.divider()
    st.caption(
        f"© 2025 [Alex Nesterovich](https://github.com/AleksNeStu) | {get_text('version', lang)} {settings.version}"
    )


if __name__ == "__main__":
    main()
