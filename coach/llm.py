import json
import logging
from typing import TypeVar
import openai
from pydantic import BaseModel, ValidationError
from coach.config import Settings
from coach.errors import CoachError

T = TypeVar("T", bound=BaseModel)


balance_blocked = False


class AIClient:
    def __init__(self, config: Settings):
        if not config.api_key:
            raise CoachError("AI 尚未连接。请在项目 .env 中设置 DEEPSEEK_API_KEY 后重试。")
        self.config = config
        logging.getLogger("openai").setLevel(logging.WARNING)
        self.client = openai.OpenAI(api_key=config.api_key, timeout=config.timeout, base_url="https://api.deepseek.com", max_retries=0)

    def generate(self, schema: type[T], system: str, payload: dict, *, max_tokens: int | None = None) -> T:
        global balance_blocked
        if balance_blocked:
            raise CoachError("余额不足，请充值后重启服务。")
        instruction = system + "\nReturn one JSON object matching this schema:\n" + json.dumps(schema.model_json_schema(), ensure_ascii=False)
        content = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if len(content) + len(instruction) > 64000:
            raise CoachError("输入过长，请精简材料或面试记录。")
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "system", "content": instruction}, {"role": "user", "content": content}],
                response_format={"type": "json_object"}, extra_body={"thinking": {"type": "disabled"}},
                max_tokens=max_tokens or self.config.max_tokens,
            )
            self.usage = {key: getattr(response.usage, key, None) for key in
                          ("prompt_tokens", "completion_tokens", "total_tokens")} if response.usage else {}
            choice = response.choices[0]
            if choice.finish_reason != "stop" or not choice.message.content:
                raise CoachError("模型输出格式未通过校验，结果未展示，请重新分析。")
            return schema.model_validate_json(choice.message.content)
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
        except openai.APIStatusError as exc:
            if exc.status_code == 402:
                balance_blocked = True
                raise CoachError("余额不足，请充值后重启服务。") from None
            raise CoachError("AI 服务暂时不可用，当前操作尚未提交，请稍后重试。") from None
        except openai.APIError:
            raise CoachError("AI 服务暂时不可用，当前操作尚未提交，请稍后重试。") from None
        except Exception:
            # Never expose SDK errors containing submitted personal data.
            raise CoachError("AI 响应无法处理，当前操作尚未提交，请重试。") from None
