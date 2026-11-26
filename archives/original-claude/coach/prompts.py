from coach.config import ROOT


def prompt(name: str) -> str:
    return (ROOT / "prompts" / "system.md").read_text(encoding="utf-8") + "\n\n" + (ROOT / "prompts" / f"{name}.md").read_text(encoding="utf-8")
