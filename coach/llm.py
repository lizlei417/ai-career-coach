import json
import logging
from typing import TypeVar
import openai
from pydantic import BaseModel, ValidationError
from coach.config import Settings
from coach.errors import CoachError

T = TypeVar("T", bound=BaseModel)


class AIClient:
    def __init__(self, config: Settings):
        if not config.api_key:
            raise CoachError("AI 尚未连接。请在项目 .env 中设置 OPENAI_API_KEY 后重试。")
        self.config = config
        logging.getLogger("openai").setLevel(logging.WARNING)
        self.client = openai.OpenAI(api_key=config.api_key, timeout=config.timeout, max_retries=1)

    def generate(self, schema: type[T], system: str, payload: dict) -> T:
        try:
            response = self.client.responses.parse(
                model=self.config.model,
                input=[{"role": "system", "content": system},
                       {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                text_format=schema,
                max_output_tokens=self.config.max_tokens,
                store=False,
            )
            if response.status != "completed" or response.output_parsed is None:
                raise CoachError("模型未返回完整的结构化结果（可能拒答或达到输出上限）。请精简材料后重试。")
            return schema.model_validate(response.output_parsed)
        except CoachError:
            raise
        except openai.AuthenticationError:
            raise CoachError("API 身份验证失败，请检查 .env 中的 API Key。") from None
        except openai.RateLimitError:
            raise CoachError("API 配额不足或请求过于频繁，请检查账户额度或稍后重试。") from None
        except openai.APITimeoutError:
            raise CoachError("AI 请求超时，当前操作尚未提交。请重试或缩短输入。") from None
        except openai.APIConnectionError:
            raise CoachError("无法连接 AI 服务，请检查网络连接后重试。") from None
        except openai.BadRequestError:
            raise CoachError("API 未接受请求，请检查模型名称及其 Structured Outputs 支持，或精简材料。") from None
        except (ValidationError, ValueError):
            raise CoachError("模型输出格式未通过校验，结果未展示，请重新分析。") from None
        except openai.APIError:
            raise CoachError("AI 服务暂时不可用，当前操作尚未提交，请稍后重试。") from None
        except Exception:
            # Never expose SDK errors containing submitted personal data.
            raise CoachError("AI 响应无法处理，当前操作尚未提交，请重试。") from None
