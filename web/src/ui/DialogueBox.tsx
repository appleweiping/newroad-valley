import { useEffect, useMemo, useRef, useState } from "react";
import { AGENTS } from "@/data/town";
import { bus } from "@/shared/bus";
import { postData } from "@/shared/api";
import { audio } from "@/game/audio";
import { SPECTATE } from "@/shared/flags";
import { useUI } from "./store";

/** Stardew-style bottom dialogue: portrait + wooden frame + typewriter text.
 * In LIVE mode an ask-box appears after the scripted lines — questions go to
 * the local bridge, which answers as the agent (LLM if a key is configured,
 * data-grounded persona templates otherwise). */
export function DialogueBox() {
  const { dialogueAgent, dialogueActivity, dialogueHearts, closeDialogue, lang, live } = useUI();
  const agent = useMemo(() => AGENTS.find((a) => a.id === dialogueAgent) ?? null, [dialogueAgent]);
  const [lineIdx, setLineIdx] = useState(0);
  const [shown, setShown] = useState(0);
  const [extraLines, setExtraLines] = useState<string[]>([]);
  const [asking, setAsking] = useState(false);
  const [question, setQuestion] = useState("");
  const [waiting, setWaiting] = useState(false);
  const timer = useRef<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const lines = useMemo(() => {
    if (!agent) return [] as string[];
    const scripted = agent.lines.map((l) => l[lang]);
    const act = dialogueActivity ? [lang === "zh" ? `（${dialogueActivity.zh}）` : `(${dialogueActivity.en})`] : [];
    // friendship flavor: warmer openers as hearts grow
    const greeting =
      dialogueHearts >= 7
        ? [lang === "zh" ? "有你在，山谷的日子格外好。" : "The valley feels brighter with you around."]
        : dialogueHearts >= 3
          ? [lang === "zh" ? "很高兴又见到你！" : "Good to see you again!"]
          : [];
    return [...greeting, ...act, ...scripted, ...extraLines];
  }, [agent, lang, dialogueActivity, dialogueHearts, extraLines]);

  const line = lines[Math.min(lineIdx, lines.length - 1)] ?? "";

  useEffect(() => {
    setLineIdx(0);
    setExtraLines([]);
    setAsking(false);
    setQuestion("");
    setWaiting(false);
  }, [dialogueAgent]);

  useEffect(() => {
    setShown(0);
    if (!agent || !line) return;
    timer.current = window.setInterval(() => {
      setShown((s) => {
        if (s >= line.length) {
          if (timer.current) window.clearInterval(timer.current);
          return s;
        }
        return s + 1;
      });
    }, 24);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [agent, line]);

  if (!agent) return null;

  const done = shown >= line.length;
  const isLast = lineIdx >= lines.length - 1;

  const close = () => {
    closeDialogue();
    bus.emit("dialogue:closed", undefined);
  };

  const advance = () => {
    if (asking || waiting) return;
    if (!done) {
      setShown(line.length);
    } else if (!isLast) {
      setLineIdx(lineIdx + 1);
    } else if (live) {
      setAsking(true);
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      close();
    }
  };

  const ask = async () => {
    const q = question.trim();
    if (!q || waiting) return;
    setWaiting(true);
    setQuestion("");
    const r = await postData<{ reply?: string }>("/api/town/dialogue", { agentId: agent.id, message: q });
    const reply = r?.reply?.trim() || (lang === "zh" ? "（信号不太好，稍后再问我吧。）" : "(Bad signal — ask me again later.)");
    setWaiting(false);
    setAsking(false);
    setExtraLines((xs) => [...xs, reply]);
    setLineIdx(lines.length); // the recomputed list gains one line — jump to it
  };

  return (
    <div
      className="fade-in"
      style={{
        position: "absolute", left: "50%", bottom: 24, transform: "translateX(-50%)",
        width: "min(720px, 92vw)", pointerEvents: "auto", cursor: asking ? "default" : "pointer",
      }}
      onClick={advance}
    >
      <div className="wood-panel" style={{ display: "flex", gap: 14, padding: 14, alignItems: "flex-start" }}>
        <div
          style={{
            width: 84, height: 84, flex: "0 0 auto", background: "var(--paper-dark)",
            border: "3px solid var(--wood)", borderRadius: 6, overflow: "hidden", position: "relative",
          }}
        >
          <img
            src={`/assets/core/characters/${agent.id}.png`}
            alt={agent.nameZh}
            style={{ position: "absolute", width: 672, height: 672, left: -42, top: -76, imageRendering: "pixelated" }}
          />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <strong style={{ fontSize: 16, color: "var(--wood-dark)" }}>
              {lang === "zh" ? agent.nameZh : agent.nameEn}
              <span className="pixel-chip" style={{ marginLeft: 8, color: agent.color, borderColor: agent.color }}>
                {lang === "zh" ? agent.roleZh : agent.role}
              </span>
              <span style={{ marginLeft: 8, fontSize: 12, color: "#c95b5b" }} title={lang === "zh" ? `好感度 ${dialogueHearts}/10` : `friendship ${dialogueHearts}/10`}>
                {"♥".repeat(Math.min(5, Math.max(0, Math.ceil(dialogueHearts / 2))))}
                <span style={{ opacity: 0.35 }}>{"♥".repeat(5 - Math.min(5, Math.max(0, Math.ceil(dialogueHearts / 2))))}</span>
              </span>
            </strong>
            <span style={{ fontSize: 11, opacity: 0.85, display: "flex", gap: 8, alignItems: "center" }} onClick={(e) => e.stopPropagation()}>
              {!SPECTATE && (
                <button
                  className="wood-btn"
                  style={{ fontSize: 11, padding: "2px 10px", background: "linear-gradient(180deg,#9be564,#5cb83a)" }}
                  title={lang === "zh" ? "接下这位居民的一单委托，种进农场" : "Take a quest from this resident"}
                  onClick={() => {
                    audio.click();
                    if (agent) bus.emit("quest:take", { agentId: agent.id });
                    closeDialogue();
                    bus.emit("dialogue:closed", undefined);
                  }}
                >
                  {lang === "zh" ? "🌱 接单" : "🌱 Quest"}
                </button>
              )}
              <span style={{ opacity: 0.65 }}>{Math.min(lineIdx + 1, lines.length)}/{lines.length}</span>
            </span>
          </div>
          <p className={done && !waiting ? "" : "typewriter-cursor"} style={{ margin: "8px 0 0", fontSize: 15, lineHeight: 1.7, minHeight: 48 }}>
            {waiting ? (lang === "zh" ? "…（思考中）" : "…(thinking)") : line.slice(0, shown)}
          </p>
          {asking && !waiting ? (
            <div style={{ display: "flex", gap: 8, marginTop: 10 }} onClick={(e) => e.stopPropagation()}>
              <input
                ref={inputRef}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void ask();
                  if (e.key === "Escape") close();
                }}
                placeholder={lang === "zh" ? `问 ${agent.nameZh} 点什么…` : `Ask ${agent.nameEn} something…`}
                style={{
                  flex: 1, padding: "6px 10px", border: "3px solid var(--wood)", borderRadius: 4,
                  background: "var(--paper-dark)", fontFamily: "inherit", fontSize: 13.5,
                  color: "var(--ink)", outline: "none",
                }}
              />
              <button className="wood-btn" onClick={() => { audio.click(); void ask(); }}>
                {lang === "zh" ? "提问" : "Ask"}
              </button>
              <button className="wood-btn" onClick={close}>✕</button>
            </div>
          ) : (
            <div style={{ textAlign: "right", fontSize: 11, opacity: 0.6 }}>
              {done
                ? isLast
                  ? live
                    ? (lang === "zh" ? "点击继续提问 ▾" : "click to ask ▾")
                    : (lang === "zh" ? "点击结束对话 ▾" : "click to end ▾")
                  : (lang === "zh" ? "点击继续 ▾" : "click to continue ▾")
                : ""}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
