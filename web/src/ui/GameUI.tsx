import { useEffect, useRef, useState } from "react";
import { bus } from "@/shared/bus";
import { BUILDINGS } from "@/data/town";
import { audio } from "@/game/audio";
import { loadSave } from "@/shared/save";
import { useUI } from "./store";
import { DialogueBox } from "./DialogueBox";
import { BuildingPanel } from "./BuildingPanel";
import { Hud } from "./Hud";
import "./pixel.css";

function PlantDialog() {
  const { plantCell, setPlantCell, lang } = useUI();
  const [title, setTitle] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (plantCell !== null) {
      setTitle("");
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [plantCell]);

  if (plantCell === null) return null;

  const cancel = () => {
    setPlantCell(null);
    bus.emit("panel:closed", undefined); // unlock the scene
  };
  const confirm = () => {
    const t = title.trim();
    setPlantCell(null);
    if (t) {
      bus.emit("farm:plant-confirm", { cell: plantCell, title: t });
    } else {
      bus.emit("panel:closed", undefined);
    }
  };

  return (
    <div
      className="fade-in"
      style={{
        position: "absolute", inset: 0, background: "rgba(20,14,28,0.45)",
        display: "flex", alignItems: "center", justifyContent: "center", pointerEvents: "auto",
      }}
      onClick={cancel}
    >
      <div className="wood-panel" style={{ width: "min(440px, 92vw)" }} onClick={(e) => e.stopPropagation()}>
        <div className="wood-title">🌱 {lang === "zh" ? "种下一个任务" : "Plant a task"}</div>
        <div style={{ padding: 16 }}>
          <p style={{ margin: "0 0 10px", fontSize: 13 }}>
            {lang === "zh"
              ? "给这株作物起个任务名。浇水 = 推进进度，成熟 = 可收获完成。"
              : "Name this crop after a task. Watering advances it; harvest when mature."}
          </p>
          <input
            ref={inputRef}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") confirm();
              if (e.key === "Escape") cancel();
            }}
            placeholder={lang === "zh" ? "例如：写完 v4 发布说明" : "e.g. finish the v4 release notes"}
            style={{
              width: "100%", boxSizing: "border-box", padding: "8px 10px",
              border: "3px solid var(--wood)", borderRadius: 4, background: "var(--paper-dark)",
              fontFamily: "inherit", fontSize: 14, color: "var(--ink)", outline: "none",
            }}
          />
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
            <button className="wood-btn" onClick={cancel}>{lang === "zh" ? "取消" : "Cancel"}</button>
            <button className="wood-btn" style={{ background: "linear-gradient(180deg,#9be564,#5cb83a)" }} onClick={confirm}>
              {lang === "zh" ? "种下 🌱" : "Plant 🌱"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Stardew-style fishing minigame: stop the bobbing marker in the green. */
function FishingBar() {
  const { fishing, setFishing, lang } = useUI();
  const [pos, setPos] = useState(0);
  const dir = useRef(1);
  const raf = useRef<number>(0);
  const active = useRef(false);

  useEffect(() => {
    if (!fishing) return;
    active.current = true;
    let p = 0;
    const tick = () => {
      if (!active.current) return;
      p += dir.current * 1.7;
      if (p >= 100) { p = 100; dir.current = -1; }
      if (p <= 0) { p = 0; dir.current = 1; }
      setPos(p);
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "e" || e.key === "E" || e.key === " " || e.key === "Enter") stop();
      if (e.key === "Escape") cancel();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      active.current = false;
      cancelAnimationFrame(raf.current);
      window.removeEventListener("keydown", onKey);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fishing]);

  if (!fishing) return null;

  const stop = () => {
    active.current = false;
    setFishing(false);
    // green zone 40-60 = perfect(2); 25-75 = ok(1); else miss(0)
    const p = posRef();
    const quality = p >= 40 && p <= 60 ? 2 : p >= 25 && p <= 75 ? 1 : 0;
    bus.emit("fishing:result", { quality });
  };
  const cancel = () => {
    active.current = false;
    setFishing(false);
    bus.emit("fishing:result", { quality: -1 });
  };
  const posRef = () => pos;

  return (
    <div
      style={{
        position: "absolute", inset: 0, display: "flex", alignItems: "center",
        justifyContent: "center", pointerEvents: "auto", background: "rgba(10,18,28,0.35)",
      }}
      onClick={stop}
    >
      <div className="wood-panel" style={{ width: "min(420px, 90vw)", padding: 18 }} onClick={(e) => e.stopPropagation()}>
        <div style={{ fontWeight: 800, color: "var(--wood-dark)", marginBottom: 10 }}>
          🎣 {lang === "zh" ? "时机！在绿区按下 E / 点击" : "Now! Press E / click in the green"}
        </div>
        <div style={{ position: "relative", height: 26, background: "var(--paper-dark)", border: "3px solid var(--wood)", borderRadius: 4 }}>
          <div style={{ position: "absolute", left: "25%", width: "50%", top: 0, bottom: 0, background: "#cfe9b8" }} />
          <div style={{ position: "absolute", left: "40%", width: "20%", top: 0, bottom: 0, background: "#8fd45e" }} />
          <div
            style={{
              position: "absolute", left: `calc(${pos}% - 4px)`, top: -4, bottom: -4, width: 8,
              background: "var(--wood-dark)", borderRadius: 2, transition: "none",
            }}
          />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10 }}>
          <span style={{ fontSize: 11, opacity: 0.65 }}>{lang === "zh" ? "正中绿心 = 稀有日志鱼" : "dead-center = rare catch"}</span>
          <button className="wood-btn" style={{ fontSize: 11 }} onClick={cancel}>{lang === "zh" ? "收竿" : "Give up"}</button>
        </div>
      </div>
    </div>
  );
}

/** Almanac: achievements + collected ores + caught fish, read from the save. */
function Almanac() {
  const { almanac, setAlmanac, lang } = useUI();
  const [tab, setTab] = useState<"ach" | "ore" | "fish">("ach");
  if (!almanac) return null;
  const save = loadSave();
  const close = () => {
    setAlmanac(false);
    bus.emit("panel:closed", undefined);
  };
  const ACH_NAMES: Record<string, string> = {
    harvest1: "第一捧收成", harvest5: "勤恳农夫（收获×5）", harvest20: "谷物大亨（收获×20）",
    ore1: "第一块技术债矿石", ore10: "债务清道夫（矿石×10）",
    fish1: "第一条日志鱼", fish10: "日志垂钓宗师（鱼×10）",
    week1: "在山谷住满一周", season1: "四季轮转之证", festival1: "赶上了丰收节",
  };
  return (
    <div
      className="fade-in"
      style={{
        position: "absolute", inset: 0, background: "rgba(20,14,28,0.45)",
        display: "flex", alignItems: "center", justifyContent: "center", pointerEvents: "auto",
      }}
      onClick={close}
    >
      <div className="wood-panel" style={{ width: "min(560px, 94vw)", maxHeight: "80vh", display: "flex", flexDirection: "column" }} onClick={(e) => e.stopPropagation()}>
        <div className="wood-title">
          <span>📖 {lang === "zh" ? "山谷图鉴" : "Valley Almanac"}</span>
          <button className="wood-btn" onClick={close}>✕</button>
        </div>
        <div style={{ display: "flex", gap: 6, padding: "10px 14px 0" }}>
          {([["ach", "🏆 成就"], ["ore", "⛏ 矿石"], ["fish", "🎣 鱼"]] as const).map(([k, label]) => (
            <button key={k} className="wood-btn" style={{ fontSize: 12, opacity: tab === k ? 1 : 0.6 }} onClick={() => setTab(k)}>
              {label}
            </button>
          ))}
          <span style={{ marginLeft: "auto", fontSize: 12, opacity: 0.7, alignSelf: "center" }}>
            {lang === "zh" ? `建设点 ${save?.points ?? 0}` : `build points ${save?.points ?? 0}`}
          </span>
        </div>
        <div className="panel-scroll" style={{ padding: 14, overflowY: "auto" }}>
          {tab === "ach" && (
            <div>
              {Object.entries(ACH_NAMES).map(([id, name]) => (
                <div key={id} className="book-card" style={{ opacity: save?.ach?.[id] ? 1 : 0.45 }}>
                  <h4>{save?.ach?.[id] ? "🏆" : "🔒"} {name}</h4>
                </div>
              ))}
            </div>
          )}
          {tab === "ore" && (
            <div>
              {(save?.ores ?? []).length === 0 && <p style={{ opacity: 0.6 }}>{lang === "zh" ? "还没有矿石——去农场西边的矿洞看看。" : "No ore yet — try the mines west of the farm."}</p>}
              {(save?.ores ?? []).map((o, i) => (
                <div key={i} className="book-card"><h4>⛏ {o}</h4></div>
              ))}
            </div>
          )}
          {tab === "fish" && (
            <div>
              {(save?.fish ?? []).length === 0 && <p style={{ opacity: 0.6 }}>{lang === "zh" ? "鱼篓还是空的——水边按 E 试试。" : "Empty creel — press E at the water's edge."}</p>}
              {(save?.fish ?? []).map((f, i) => (
                <div key={i} className="book-card"><h4>🎣 {f}</h4></div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Toast() {
  const { toast } = useUI();
  if (!toast) return null;
  return (
    <div
      className="wood-panel fade-in"
      style={{
        position: "absolute", top: 16, left: "50%", transform: "translateX(-50%)",
        padding: "8px 18px", fontSize: 13.5, maxWidth: "80vw", pointerEvents: "none",
      }}
    >
      {toast}
    </div>
  );
}

export function GameUI() {
  const { openDialogue, openBuilding, setClock, setLive, setPlantCell, setToast, setFishing } = useUI();

  useEffect(() => {
    let toastTimer: number | undefined;
    const offs = [
      bus.on("npc:talk", ({ agentId, activityZh, activityEn }) =>
        openDialogue(agentId, activityZh ? { zh: activityZh, en: activityEn ?? activityZh } : null)),
      bus.on("building:enter", ({ buildingId }) => openBuilding(buildingId)),
      bus.on("building:enter-panel", ({ panel }) => {
        const b = BUILDINGS.find((bb) => bb.panel === panel);
        if (b) openBuilding(b.id);
      }),
      bus.on("clock:tick", (c) => setClock(c)),
      bus.on("mode:detected", ({ live }) => setLive(live)),
      bus.on("farm:plant-request", ({ cell }) => {
        audio.click();
        setPlantCell(cell);
      }),
      bus.on("fishing:start", () => setFishing(true)),
      bus.on("toast", ({ text }) => {
        setToast(text);
        window.clearTimeout(toastTimer);
        toastTimer = window.setTimeout(() => setToast(null), 2600);
      }),
    ];
    return () => {
      offs.forEach((off) => off());
      window.clearTimeout(toastTimer);
    };
  }, [openDialogue, openBuilding, setClock, setLive, setPlantCell, setToast]);

  return (
    <div className="pixel-font" style={{ position: "fixed", inset: 0, pointerEvents: "none" }}>
      <Hud />
      <Toast />
      <DialogueBox />
      <BuildingPanel />
      <PlantDialog />
      <FishingBar />
      <Almanac />
    </div>
  );
}
