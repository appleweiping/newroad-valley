import { useEffect, useRef, useState } from "react";
import { bus } from "@/shared/bus";
import { BUILDINGS } from "@/data/town";
import { audio } from "@/game/audio";
import { loadSave } from "@/shared/save";
import { getData } from "@/shared/api";
import { SPECTATE } from "@/shared/flags";
import { useUI } from "./store";
import { DialogueBox } from "./DialogueBox";
import { BuildingPanel } from "./BuildingPanel";
import { Hud } from "./Hud";
import { TouchControls } from "./TouchControls";
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
    const offTouch = bus.on("touch:interact", () => stop()); // touch E button reels in too
    return () => {
      active.current = false;
      cancelAnimationFrame(raf.current);
      window.removeEventListener("keydown", onKey);
      offTouch();
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

/** The Valley Handbook: bag / shipping / shop / museum / achievements / almanac.
 * Reads the save fresh each render; actions go through the bus to the scene,
 * and a local nonce re-renders after each mutation. */
interface ChronicleEntry { date: string; kind: string; title: string; detail: string }

function Almanac() {
  const { almanac, setAlmanac, almanacTab, setAlmanacTab, lang } = useUI();
  const [, setNonce] = useState(0);
  const [chronicle, setChronicle] = useState<ChronicleEntry[] | null>(null);
  useEffect(() => {
    if (!almanac || almanacTab !== "chronicle" || chronicle) return;
    getData<{ entries: ChronicleEntry[] }>("/api/town/chronicle", "chronicle.json")
      .then((d) => setChronicle(d.entries ?? []))
      .catch(() => setChronicle([]));
  }, [almanac, almanacTab, chronicle]);
  if (!almanac) return null;
  const tab = almanacTab;
  const setTab = setAlmanacTab;
  const bump = () => setNonce((n) => n + 1);
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
    museum8: "镇立博物馆开馆（馆藏×8）",
  };
  const KIND_ICON: Record<string, string> = { crop: "🌾", ore: "⛏", fish: "🎣" };
  const SHOP_ITEMS = [
    { id: "can2", icon: "💧", name: lang === "zh" ? "浇水壶 II（一次浇 3 格）" : "Watering Can II (3 cells)", cost: 20, owned: (save?.canLevel ?? 1) >= 2 },
    { id: "lamp", icon: "🏮", name: lang === "zh" ? "广场灯串（一盏）" : "Plaza lamp (one)", cost: 8, owned: false },
    { id: "flower", icon: "🌷", name: lang === "zh" ? "南广场花坛（一座）" : "South-plaza flowerbed", cost: 6, owned: false },
  ];
  return (
    <div
      className="fade-in"
      style={{
        position: "absolute", inset: 0, background: "rgba(20,14,28,0.45)",
        display: "flex", alignItems: "center", justifyContent: "center", pointerEvents: "auto",
      }}
      onClick={close}
    >
      <div className="wood-panel" style={{ width: "min(620px, 94vw)", maxHeight: "82vh", display: "flex", flexDirection: "column" }} onClick={(e) => e.stopPropagation()}>
        <div className="wood-title">
          <span>📖 {lang === "zh" ? "山谷手册" : "Valley Handbook"}</span>
          <button className="wood-btn" onClick={close}>✕</button>
        </div>
        <div style={{ display: "flex", gap: 5, padding: "10px 14px 0", flexWrap: "wrap" }}>
          {([["bag", "🎒 背包"], ["ship", "📦 出货"], ["shop", "🛒 商店"], ["museum", "🏛 博物馆"], ["chronicle", "📜 镇志"], ["ach", "🏆 成就"], ["ore", "⛏ 矿石"], ["fish", "🎣 鱼"]] as const).map(([k, label]) => (
            <button key={k} className="wood-btn" style={{ fontSize: 11.5, opacity: tab === k ? 1 : 0.6 }} onClick={() => setTab(k)}>
              {label}
            </button>
          ))}
          <span style={{ marginLeft: "auto", fontSize: 12, opacity: 0.7, alignSelf: "center" }}>
            {lang === "zh" ? `建设点 ${save?.points ?? 0}` : `pts ${save?.points ?? 0}`}
          </span>
        </div>
        <div className="panel-scroll" style={{ padding: 14, overflowY: "auto" }}>
          {tab === "bag" && (
            <div>
              {(save?.inventory ?? []).length === 0 && (
                <p style={{ opacity: 0.6 }}>{lang === "zh" ? "背包是空的——收获、挖矿、钓鱼都会入包。" : "Empty bag — harvests, ore and fish land here."}</p>
              )}
              {(save?.inventory ?? []).map((it, i) => (
                <div key={i} className="book-card" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <h4 style={{ flex: 1, margin: 0 }}>{KIND_ICON[it.kind] ?? "❔"} {it.name}</h4>
                  <button className="wood-btn" style={{ fontSize: 11 }} onClick={() => { bus.emit("ship:add", { index: i }); setTimeout(bump, 80); }}>
                    {lang === "zh" ? "投入出货箱" : "Ship"}
                  </button>
                </div>
              ))}
            </div>
          )}
          {tab === "ship" && (
            <div>
              <p style={{ fontSize: 12.5, opacity: 0.75, marginTop: 0 }}>
                {lang === "zh" ? "投进箱里的货品，第二天清晨结算成建设点（矿石 3 点，其余 2 点）。" : "Bin contents pay out next morning (ore 3 pts, others 2)."}
              </p>
              <button className="wood-btn" style={{ marginBottom: 10 }} onClick={() => { bus.emit("ship:all", undefined); setTimeout(bump, 80); }}>
                {lang === "zh" ? "📦 背包全部投入" : "📦 Ship everything"}
              </button>
              {(save?.pendingShip ?? []).length === 0
                ? <p style={{ opacity: 0.6 }}>{lang === "zh" ? "箱子是空的。" : "The bin is empty."}</p>
                : (save?.pendingShip ?? []).map((it, i) => (
                  <div key={i} className="book-card"><h4>{KIND_ICON[it.kind] ?? "❔"} {it.name}</h4></div>
                ))}
            </div>
          )}
          {tab === "shop" && (
            <div>
              <p style={{ fontSize: 12.5, opacity: 0.75, marginTop: 0 }}>
                {lang === "zh" ? "建设点换好物——工具进背包，摆件直接装点小镇。" : "Spend build points — tools to your hand, decor straight into town."}
              </p>
              {SHOP_ITEMS.map((it) => (
                <div key={it.id} className="book-card" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <h4 style={{ flex: 1, margin: 0 }}>{it.icon} {it.name}</h4>
                  <span style={{ fontSize: 12, opacity: 0.7 }}>{it.cost} {lang === "zh" ? "点" : "pts"}</span>
                  <button
                    className="wood-btn" style={{ fontSize: 11, opacity: it.owned ? 0.5 : 1 }}
                    disabled={it.owned}
                    onClick={() => { bus.emit("shop:buy", { itemId: it.id }); setTimeout(bump, 80); }}
                  >
                    {it.owned ? (lang === "zh" ? "已拥有" : "Owned") : lang === "zh" ? "购买" : "Buy"}
                  </button>
                </div>
              ))}
            </div>
          )}
          {tab === "museum" && (
            <div>
              <p style={{ fontSize: 12.5, opacity: 0.75, marginTop: 0 }}>
                {lang === "zh" ? `馆藏 ${(save?.museum?.ores ?? []).length + (save?.museum?.fish ?? []).length} 件 · 每件捐赠 +2 建设点，集满 8 件开馆成就。` : "Each donation +2 pts; 8 pieces open the museum."}
              </p>
              <h4 style={{ margin: "6px 0" }}>{lang === "zh" ? "🏛 展品墙" : "🏛 The wall"}</h4>
              {[...(save?.museum?.ores ?? []).map((o) => `⛏ ${o}`), ...(save?.museum?.fish ?? []).map((f) => `🎣 ${f}`)].map((s, i) => (
                <div key={i} className="book-card"><h4>{s}</h4></div>
              ))}
              <h4 style={{ margin: "10px 0 6px" }}>{lang === "zh" ? "可捐赠（来自图鉴）" : "Donatable (from collections)"}</h4>
              {(save?.ores ?? []).map((o, i) => !(save?.museum?.ores ?? []).includes(o) && (
                <div key={`o${i}`} className="book-card" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <h4 style={{ flex: 1, margin: 0 }}>⛏ {o}</h4>
                  <button className="wood-btn" style={{ fontSize: 11 }} onClick={() => { bus.emit("museum:donate", { kind: "ore", index: i }); setTimeout(bump, 80); }}>
                    {lang === "zh" ? "捐赠" : "Donate"}
                  </button>
                </div>
              ))}
              {(save?.fish ?? []).map((f, i) => !(save?.museum?.fish ?? []).includes(f) && (
                <div key={`f${i}`} className="book-card" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <h4 style={{ flex: 1, margin: 0 }}>🎣 {f}</h4>
                  <button className="wood-btn" style={{ fontSize: 11 }} onClick={() => { bus.emit("museum:donate", { kind: "fish", index: i }); setTimeout(bump, 80); }}>
                    {lang === "zh" ? "捐赠" : "Donate"}
                  </button>
                </div>
              ))}
            </div>
          )}
          {tab === "chronicle" && (
            <div>
              <p style={{ fontSize: 12.5, opacity: 0.75, marginTop: 0 }}>
                {lang === "zh" ? "Fable 笔下的小镇编年史——每一行都来自真实的发布与里程碑。" : "Fable's town chronicle — every line is a real release or milestone."}
              </p>
              {chronicle === null && <p style={{ opacity: 0.6 }}>{lang === "zh" ? "翻书中……" : "Turning pages…"}</p>}
              {chronicle?.length === 0 && <p style={{ opacity: 0.6 }}>{lang === "zh" ? "镇志暂时翻不开。" : "The chronicle won't open right now."}</p>}
              {(chronicle ?? []).map((e, i) => (
                <div key={i} className="book-card">
                  <h4>
                    {e.kind === "release" ? "🚀" : e.kind === "milestone" ? "⭐" : "🏛"} {e.title}
                    <span style={{ fontWeight: 400, fontSize: 11, opacity: 0.6, marginLeft: 8 }}>{e.date}</span>
                  </h4>
                  {e.detail && <p style={{ margin: "4px 0 0", fontSize: 12, opacity: 0.8 }}>{e.detail}</p>}
                </div>
              ))}
            </div>
          )}
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
              {(save?.ores ?? []).length === 0 && <p style={{ opacity: 0.6 }}>{lang === "zh" ? "还没有矿石——去农场南边的矿洞看看。" : "No ore yet — try the mines south of the farm."}</p>}
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

/** v9: onboarding quest tracker — Fable's 5-step welcome tour */
function TutorialBanner() {
  const { lang } = useUI();
  const [t, setT] = useState<{ step: number; total: number; textZh: string; textEn: string } | null>(null);
  useEffect(() => bus.on("tutorial:step", (p) => setT(p.step >= 99 ? null : p)), []);
  if (!t) return null;
  return (
    <div
      className="wood-panel fade-in"
      style={{ position: "absolute", top: 12, left: 12, padding: "7px 12px", fontSize: 12.5, pointerEvents: "none", maxWidth: 290 }}
    >
      🧭 {lang === "zh" ? `新手任务 ${t.step}/${t.total}：${t.textZh}` : `Quest ${t.step}/${t.total}: ${t.textEn}`}
    </div>
  );
}

/** v9: settings — volume, language, zoom, tutorial reset */
function SettingsDialog() {
  const { settings, setSettings, lang, setLang } = useUI();
  const [vol, setVol] = useState(() => Math.round(audio.volume * 100));
  if (!settings) return null;
  const close = () => {
    setSettings(false);
    bus.emit("panel:closed", undefined);
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
      <div className="wood-panel" style={{ width: "min(420px, 92vw)" }} onClick={(e) => e.stopPropagation()}>
        <div className="wood-title">
          <span>⚙ {lang === "zh" ? "设置" : "Settings"}</span>
          <button className="wood-btn" onClick={close}>✕</button>
        </div>
        <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 14 }}>
          <label style={{ fontSize: 13 }}>
            🔊 {lang === "zh" ? "音量" : "Volume"} · {vol}%
            <input
              type="range" min={0} max={100} value={vol}
              style={{ width: "100%", accentColor: "#5cb83a" }}
              onChange={(e) => {
                const v = Number(e.target.value);
                setVol(v);
                audio.setVolume(v / 100);
              }}
            />
          </label>
          <div style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
            🌐 {lang === "zh" ? "语言" : "Language"}
            <button className="wood-btn" style={{ fontSize: 12, opacity: lang === "zh" ? 1 : 0.55 }} onClick={() => setLang("zh")}>中文</button>
            <button className="wood-btn" style={{ fontSize: 12, opacity: lang === "en" ? 1 : 0.55 }} onClick={() => setLang("en")}>English</button>
          </div>
          <div style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
            🔍 {lang === "zh" ? "像素缩放" : "Pixel zoom"}
            {[2, 3, 4].map((z) => (
              <button key={z} className="wood-btn" style={{ fontSize: 12 }} onClick={() => bus.emit("settings:zoom", { zoom: z })}>
                {z}×
              </button>
            ))}
          </div>
          <div style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
            🧭 {lang === "zh" ? "新手引导" : "Onboarding"}
            <button className="wood-btn" style={{ fontSize: 12 }} onClick={() => { bus.emit("tutorial:skip", undefined); close(); }}>
              {lang === "zh" ? "跳过引导" : "Skip the tour"}
            </button>
          </div>
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
  const { openDialogue, openBuilding, setClock, setLive, setPlantCell, setToast, setFishing, setAlmanac, setAlmanacTab, setStamina } = useUI();

  useEffect(() => {
    let toastTimer: number | undefined;
    const offs = [
      bus.on("npc:talk", ({ agentId, activityZh, activityEn, hearts }) =>
        // interior scenes emit without hearts — fall back to the save
        openDialogue(
          agentId,
          activityZh ? { zh: activityZh, en: activityEn ?? activityZh } : null,
          hearts ?? loadSave()?.hearts?.[agentId] ?? 0,
        )),
      bus.on("building:enter", ({ buildingId }) => openBuilding(buildingId)),
      bus.on("building:enter-panel", ({ panel }) => {
        if (panel === "museum") {
          // the museum desk opens the handbook's museum page
          setAlmanacTab("museum");
          setAlmanac(true);
          return;
        }
        const b = BUILDINGS.find((bb) => bb.panel === panel);
        if (b) openBuilding(b.id);
      }),
      bus.on("clock:tick", (c) => setClock(c)),
      bus.on("mode:detected", ({ live }) => setLive(live)),
      bus.on("farm:plant-request", ({ cell }) => {
        if (SPECTATE) {
          bus.emit("toast", { text: "👀 观战模式为只读 · spectate is read-only" });
          bus.emit("panel:closed", undefined); // unlock the scene
          return;
        }
        audio.click();
        setPlantCell(cell);
      }),
      bus.on("fishing:start", () => setFishing(true)),
      bus.on("stamina:changed", ({ value }) => setStamina(value)),
      bus.on("almanac:tab", ({ tab }) => {
        setAlmanacTab(tab);
        setAlmanac(true);
      }),
      bus.on("toast", ({ text }) => {
        setToast(text);
        window.clearTimeout(toastTimer);
        toastTimer = window.setTimeout(() => setToast(null), 2600);
      }),
    ];
    // surface the saved stamina on boot
    setStamina(loadSave()?.stamina ?? 100);
    return () => {
      offs.forEach((off) => off());
      window.clearTimeout(toastTimer);
    };
  }, [openDialogue, openBuilding, setClock, setLive, setPlantCell, setToast, setAlmanac, setAlmanacTab, setStamina]);

  return (
    <div className="pixel-font" style={{ position: "fixed", inset: 0, pointerEvents: "none" }}>
      <Hud />
      <Toast />
      <DialogueBox />
      <BuildingPanel />
      <PlantDialog />
      <FishingBar />
      <Almanac />
      <TutorialBanner />
      <SettingsDialog />
      <TouchControls />
    </div>
  );
}
