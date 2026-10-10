"""Conectores de API especializados para la tríada de modelos:
- GLM-5.3: Arquitecto Líder (diseña arquitectura, divide trabajo, decisiones de integración).
- GLM-5.3-flash: Implementador / Developer (componentes, código concreto, tests, fixes rápidos).
- Kimi-k3: Auditor Independiente (análisis lógico, revisión de código, detección de fallos y huecos).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from openai import OpenAI
from config.settings import settings


class AgentModelConnector:
    """Cliente unificado para comunicación con modelos de NVIDIA NIM con razonamiento y modo JSON."""

    def __init__(self, model_name: str, api_key: str, role_title: str):
        self.model_name = model_name
        self.api_key = api_key or getattr(settings, "NVIDIA_API_KEY", "")
        self.role_title = role_title
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=self.api_key,
            timeout=180.0,
        )
        self.last_reasoning: str = ""
        self.last_content: str = ""

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.4,
        max_tokens: int = 4096,
        json_mode: bool = False,
        on_reasoning: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Envía prompt al modelo y extrae la respuesta asegurando contenido limpio."""
        sys_msg = system_prompt
        if json_mode:
            sys_msg += "\nDEBES RESPONDER EXCLUSIVAMENTE CON UN OBJETO JSON VÁLIDO. Sin explicaciones previas ni posteriores, sin bloques markdown innecesarios."

        kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        collected_content = []
        collected_reasoning = []

        try:
            stream_resp = self.client.chat.completions.create(**kwargs)
            for chunk in stream_resp:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                c = getattr(delta, "content", None) or ""
                r = getattr(delta, "reasoning_content", None) or ""
                if c:
                    collected_content.append(c)
                if r:
                    collected_reasoning.append(r)
                    self.last_reasoning = "".join(collected_reasoning)
                    if on_reasoning:
                        try:
                            on_reasoning(self.last_reasoning)
                        except Exception:
                            pass
        except Exception as exc:
            # Si el streaming falla por alguna causa de red, intentar sin stream
            if not collected_content and not collected_reasoning:
                kwargs["stream"] = False
                resp = self.client.chat.completions.create(**kwargs)
                choice = resp.choices[0]
                content = choice.message.content or ""
                reasoning = getattr(choice.message, "reasoning_content", None) or ""
                collected_content = [content]
                collected_reasoning = [reasoning]

        content = "".join(collected_content).strip()
        reasoning = "".join(collected_reasoning).strip()
        self.last_reasoning = reasoning
        self.last_content = content

        # Si tenemos content con JSON, usar content
        target_text = content
        # Si content no tiene JSON pero reasoning sí, buscar en reasoning
        if not target_text or ("{" not in target_text):
            if "{" in reasoning:
                target_text = reasoning
            elif not target_text:
                target_text = reasoning

        if json_mode:
            # 1. Intentar bloque markdown
            m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", target_text)
            if m:
                clean_text = m.group(1).strip()
            else:
                # 2. Si hay un bloque JSON con llaves dentro de texto explicativo
                start_b = target_text.find("{")
                end_b = target_text.rfind("}")
                if start_b != -1 and end_b != -1 and end_b > start_b:
                    clean_text = target_text[start_b : end_b + 1].strip()
                else:
                    clean_text = target_text
        else:
            clean_text = target_text

        return clean_text

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        on_reasoning: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        raw = self.generate(
            system_prompt,
            user_prompt,
            temperature=0.2,
            max_tokens=max_tokens,
            json_mode=True,
            on_reasoning=on_reasoning,
        )
        clean_str = raw.strip()
        # Intentar cargar directo
        try:
            return json.loads(clean_str)
        except Exception:
            pass

        # Si viene rodeado de markdown
        m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", clean_str)
        if m:
            clean_str = m.group(1).strip()
            try:
                return json.loads(clean_str)
            except Exception:
                pass

        # Buscar substring desde primer { hasta último }
        start = clean_str.find("{")
        end = clean_str.rfind("}")
        if start != -1 and end != -1 and end > start:
            sub = clean_str[start : end + 1]
            try:
                return json.loads(sub)
            except Exception:
                # Limpiar comas sobrantes antes de } o ]
                fixed = re.sub(r",\s*([\}\]])", r"\1", sub)
                try:
                    return json.loads(fixed)
                except Exception:
                    pass

        # Si no parseó como JSON convencional, verificar si el modelo devolvió código puro
        # en bloques markdown ```lenguaje ... ``` o ``` ... ```
        code_blocks = re.findall(r"```(?:\w+)?\n([\s\S]*?)```", clean_str)
        if code_blocks:
            # Reconstruir diccionario mapeando a target_files o primer archivo
            merged_code = "\n".join(code_blocks).strip()
            if merged_code:
                return {"_raw_code_": merged_code}

        raise ValueError(f"No se pudo parsear respuesta JSON de {self.role_title}: {raw[:300]}")


def get_architect_model() -> AgentModelConnector:
    """GLM-5.3: Diseñador de arquitectura, división de tareas y decisiones estructurales."""
    key = getattr(settings, "GLM_API_KEY", "") or getattr(settings, "NVIDIA_API_KEY", "")
    return AgentModelConnector(
        model_name="z-ai/glm-5.3",
        api_key=key,
        role_title="Arquitecto Líder (GLM-5.3)",
    )


def get_implementer_model() -> AgentModelConnector:
    """GLM-5.3-flash: Implementador veloz de componentes, lógica y correcciones."""
    key = getattr(settings, "GLM_FLASH_API_KEY", "") or getattr(settings, "NVIDIA_API_KEY", "")
    return AgentModelConnector(
        model_name="z-ai/glm-5.3-flash",
        api_key=key,
        role_title="Implementador Developer (GLM-5.3-flash)",
    )


def get_auditor_model() -> AgentModelConnector:
    """Kimi-k3: Auditor riguroso, revisión de consistencia y búsqueda de fallos."""
    key = getattr(settings, "KIMI_API_KEY", "") or getattr(settings, "NVIDIA_API_KEY", "")
    return AgentModelConnector(
        model_name="moonshotai/kimi-k3",
        api_key=key,
        role_title="Auditor QA (Kimi-k3)",
    )


def get_planner_model() -> AgentModelConnector:
    """Alias para GLM-5.3-flash como planificador ágil."""
    return get_implementer_model()

