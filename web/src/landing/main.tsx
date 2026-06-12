import { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { AGENTS, BUILDINGS } from "@/data/town";
import "@/ui/pixel.css";
import "./landing.css";

type Lang = "zh" | "en";

const T = {
  zh: {
    tag: "把真实工作种进像素山谷",
    sub: "一座星露谷风格的像素小镇，背后是一套真实运转的本地工作系统：agent 协作、长期记忆、wiki 知识塔、科研看板、技能配方与代码仓库。走进去，和你的 AI 们一起生活与干活。",
    cta: "▶ 进入小镇",
    demoTitle: "小镇就在这里 · 即点即玩",
    demoSub: "拖拽平移 · 滚轮缩放 · 点击建筑 · 和 agent 对话 —— 这是真正的游戏画面，不是录像",
    demoStart: "▶ 启动小镇",
    agentsTitle: "八位 agent 居民",
    agentsSub: "他们不是虚构角色——每一位都对应这台机器上真实存在的 agent 启动器",
    bldTitle: "十栋工作建筑",
    bldSub: "每栋建筑都是一个真实系统的入口：点击卡片展开它连接的数据源",
    archTitle: "它是怎么运转的",
    archSub: "公开站点跑演示快照；在本机运行时自动连接真实数据桥",
    roadTitle: "建设日志",
    statsTitle: "镇志数据",
    credits: "美术资产致谢",
  },
  en: {
    tag: "Plant your real work into a pixel valley",
    sub: "A Stardew-style pixel town running on a real local work system: agent collaboration, long-term memory, a wiki tower, research boards, skill recipes and git repos. Walk in and live with your AIs.",
    cta: "▶ Enter the town",
    demoTitle: "The town is right here · play instantly",
    demoSub: "Drag to pan · wheel to zoom · click buildings · talk to agents — real gameplay, not a video",
    demoStart: "▶ Start the town",
    agentsTitle: "Eight agent residents",
    agentsSub: "Not fictional characters — each maps to a real agent launcher on this machine",
    bldTitle: "Ten working buildings",
    bldSub: "Every building is a doorway into a real system. Click a card to expand its data sources",
    archTitle: "How it works",
    archSub: "The public site runs demo snapshots; on the owner's machine it auto-connects to the live bridge",
    roadTitle: "Build log",
    statsTitle: "Town almanac",
    credits: "Art credits",
  },
};

function Stars() {
  const stars = useMemo(
    () =>
      Array.from({ length: 40 }, (_, i) => ({
        left: `${(i * 37 + 13) % 100}%`,
        top: `${(i * 23 + 7) % 55}%`,
        delay: `${(i % 10) * 0.33}s`,
      })),
    [],
  );
  return (
    <div className="l-stars">
      {stars.map((s, i) => (
        <div key={i} className="l-star" style={{ left: s.left, top: s.top, animationDelay: s.delay }} />
      ))}
    </div>
  );
}

function AgentCard({ a, lang }: { a: (typeof AGENTS)[number]; lang: Lang }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="l-card" onClick={() => setOpen(!open)} style={{ borderLeftWidth: 6, borderLeftColor: a.color }}>
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <div className="l-agent-face">
          <img src={`/assets/core/characters/${a.id}.png`} alt={a.nameEn} />
        </div>
        <div>
          <h3 style={{ margin: 0 }}>{lang === "zh" ? a.nameZh : a.nameEn}</h3>
          <span className="pixel-chip" style={{ color: a.color, borderColor: a.color }}>
            {lang === "zh" ? a.roleZh : a.role}
          </span>
        </div>
      </div>
      <p style={{ marginTop: 10 }}>{lang === "zh" ? a.bioZh : a.bioEn}</p>
      {open && (
        <div className="more">
          <div style={{ fontFamily: "monospace", fontSize: 11.5 }}>{a.launcher}</div>
          <div style={{ marginTop: 6, fontStyle: "italic" }}>
            “{lang === "zh" ? a.lines[0].zh : a.lines[0].en}”
          </div>
        </div>
      )}
      <div style={{ marginTop: 8, fontSize: 11, opacity: 0.6 }}>{open ? "▲" : `▼ ${lang === "zh" ? "展开档案" : "expand"}`}</div>
    </div>
  );
}

function BuildingCard({ b, lang }: { b: (typeof BUILDINGS)[number]; lang: Lang }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="l-card" onClick={() => setOpen(!open)}>
      <div style={{ display: "flex", justifyContent: "center", minHeight: 96, alignItems: "flex-end", marginBottom: 10 }}>
        <img
          src={`/assets/core/buildings/${b.id}.png`}
          alt={b.nameEn}
          style={{ imageRendering: "pixelated", height: 96, objectFit: "contain" }}
        />
      </div>
      <h3>{lang === "zh" ? b.nameZh : b.nameEn}</h3>
      <p>{lang === "zh" ? b.descZh : b.descEn}</p>
      {open && (
        <div className="more">
          {b.sources.map((s) => (
            <div key={s} style={{ fontFamily: "monospace", fontSize: 11.5 }}>⛁ {s}</div>
          ))}
        </div>
      )}
      <div style={{ marginTop: 8, fontSize: 11, opacity: 0.6 }}>{open ? "▲" : `▼ ${lang === "zh" ? "数据源" : "sources"}`}</div>
    </div>
  );
}

function Demo({ lang }: { lang: Lang }) {
  const [started, setStarted] = useState(false);
  return (
    <div className="l-iframe-wrap">
      {started ? (
        <iframe src="/play.html" title="Newroad Valley" allow="fullscreen" />
      ) : (
        <div className="l-iframe-cover" onClick={() => setStarted(true)}>
          <img
            src="/assets/core/buildings/town-hall.png"
            alt=""
            style={{ imageRendering: "pixelated", height: 140 }}
          />
          <button className="wood-btn" style={{ fontSize: 20, padding: "12px 34px" }}>
            {T[lang].demoStart}
          </button>
          <div style={{ fontSize: 12.5, opacity: 0.8 }}>{T[lang].demoSub}</div>
        </div>
      )}
    </div>
  );
}

function Arch({ lang }: { lang: Lang }) {
  const zh = lang === "zh";
  return (
    <div className="l-arch">
      <div className="l-arch-row">
        <div className="l-arch-box"><b>{zh ? "浏览器 · 像素小镇" : "Browser · pixel town"}</b>Phaser 3 + React</div>
      </div>
      <div className="l-arch-link">▲▼</div>
      <div className="l-arch-row">
        <div className="l-arch-box"><b>{zh ? "演示快照" : "Demo snapshots"}</b>/demo/*.json（{zh ? "脱敏" : "sanitized"}）</div>
        <div className="l-arch-box"><b>{zh ? "本地数据桥" : "Live local bridge"}</b>FastAPI :8000</div>
      </div>
      <div className="l-arch-link">▲▼</div>
      <div className="l-arch-row">
        <div className="l-arch-box"><b>agentmemory</b>:3111 · 53 tools</div>
        <div className="l-arch-box"><b>WEIPING_WIKI</b>{zh ? "知识库" : "knowledge"}</div>
        <div className="l-arch-box"><b>{zh ? "科研看板" : "Research boards"}</b>{zh ? "仅元数据" : "metadata only"}</div>
        <div className="l-arch-box"><b>{zh ? "技能索引" : "Skill index"}</b>133 recipes</div>
        <div className="l-arch-box"><b>Git</b>{zh ? "本地仓库" : "local repos"}</div>
      </div>
    </div>
  );
}

const ROADMAP: { zh: string; en: string; date: string; done: boolean; descZh: string; descEn: string }[] = [
  { zh: "v1 · React/Phaser 原型", en: "v1 · React/Phaser prototype", date: "2026-05", done: true, descZh: "第一版竖切：地图、随机游走 NPC、只读适配器。", descEn: "First slice: map, random-walk NPCs, read-only adapters." },
  { zh: "v2 · Godot 重建（35 栋建筑）", en: "v2 · Godot rebuild (35 buildings)", date: "2026-05", done: true, descZh: "FastAPI 180+ 端点 + 真实数据适配器；绘本画风（后被推翻）。", descEn: "FastAPI 180+ endpoints + real adapters; storybook art (later replaced)." },
  { zh: "v3 · 星露谷式 Web 重生", en: "v3 · Stardew-style web rebirth", date: "2026-06", done: true, descZh: "迁居 D:\\Company；真像素美术；八位居民各有专属物种；浏览器即点即玩；agentmemory 修复加固。", descEn: "Moved to D:\\Company; true pixel art; eight residents with unique species; instant browser play; agentmemory hardened." },
  { zh: "v4 · 室内与活水", en: "v4 · Interiors & Living Data", date: "2026-06", done: true, descZh: "六个可进入室内（书架长廊/锻造间/状态大厅/卧室存档）；作物=真实任务双向联动；NPC 日程与 A* 寻路；对话桥可提问；全 CC0 音频；存档系统。", descEn: "Six enterable interiors (stacks, forge, status hall, bedroom saves); crops bound to real tasks; NPC schedules & A* pathfinding; ask-the-agent dialogue; CC0 audio; save system." },
  { zh: "v5 · 矿洞与季节", en: "v5 · Mines & Seasons", date: "2026-06", done: true, descZh: "三层技术债矿洞（矿石=真实 TODO/FIXME 与 git 热点）；日志钓鱼时机条（ERROR=金鱼王）；四季调色与降雪；GitHub 发布日=丰收节烟花；十枚成就+年鉴图鉴；存档 v2。", descEn: "Three-level tech-debt mines (ore = real TODO/FIXME & git hotspots); log-fishing timing bar (ERROR = king fish); seasonal palettes & snowfall; GitHub release day = festival fireworks; ten achievements + almanac; save v2." },
  { zh: "v6 · 远行与同行（下一个大版本）", en: "v6 · Mobile & Spectate (next)", date: "排队中", done: false, descZh: "移动端虚拟摇杆与触控、PWA 离线、只读观战分享链接、agentmemory 信号实时可视化——agent 接单瞬间 NPC 跑向公告板。", descEn: "Mobile joystick & touch, PWA offline, read-only spectate links, live agentmemory signals — NPCs dash to the notice board the moment an agent takes a job." },
];

function Landing() {
  const [lang, setLang] = useState<Lang>("zh");
  const t = T[lang];
  return (
    <div className="landing pixel-font">
      <div className="l-langbar">
        <button className="wood-btn" onClick={() => setLang(lang === "zh" ? "en" : "zh")}>
          {lang === "zh" ? "EN" : "中文"}
        </button>
        <a className="wood-btn" style={{ textDecoration: "none" }} href="https://github.com/appleweiping/newroad-valley" target="_blank" rel="noreferrer">
          GitHub
        </a>
      </div>

      <header className="l-hero">
        <Stars />
        <div style={{ fontSize: 14, letterSpacing: "0.3em", opacity: 0.8 }}>Newroad Valley · v3</div>
        <h1>新路谷物语</h1>
        <div className="sub">{t.tag} — {t.sub}</div>
        <a className="wood-btn l-cta" href="/play.html">{t.cta}</a>
        <div className="l-marquee">
          <div className="l-stat"><b>8</b><span>{lang === "zh" ? "agent 居民" : "agent residents"}</span></div>
          <div className="l-stat"><b>10</b><span>{lang === "zh" ? "工作建筑" : "working buildings"}</span></div>
          <div className="l-stat"><b>440+</b><span>{lang === "zh" ? "记忆馆藏" : "memories shelved"}</span></div>
          <div className="l-stat"><b>741</b><span>{lang === "zh" ? "wiki 页面" : "wiki pages"}</span></div>
          <div className="l-stat"><b>133</b><span>{lang === "zh" ? "技能配方" : "skill recipes"}</span></div>
        </div>
      </header>

      <section className="l-section">
        <h2 className="l-h2">{t.demoTitle}</h2>
        <p className="l-h2sub">{t.demoSub}</p>
        <Demo lang={lang} />
      </section>

      <section className="l-section">
        <h2 className="l-h2">{t.agentsTitle}</h2>
        <p className="l-h2sub">{t.agentsSub}</p>
        <div className="l-grid cols3">
          {AGENTS.map((a) => (
            <AgentCard key={a.id} a={a} lang={lang} />
          ))}
        </div>
      </section>

      <section className="l-section">
        <h2 className="l-h2">{t.bldTitle}</h2>
        <p className="l-h2sub">{t.bldSub}</p>
        <div className="l-grid cols4">
          {BUILDINGS.map((b) => (
            <BuildingCard key={b.id} b={b} lang={lang} />
          ))}
        </div>
      </section>

      <section className="l-section">
        <h2 className="l-h2">{t.archTitle}</h2>
        <p className="l-h2sub">{t.archSub}</p>
        <Arch lang={lang} />
      </section>

      <section className="l-section" style={{ maxWidth: 760 }}>
        <h2 className="l-h2">{t.roadTitle}</h2>
        <div className="l-timeline" style={{ marginTop: 28 }}>
          {ROADMAP.map((r, i) => (
            <div key={i} className={`l-tl-item${r.done ? " done" : ""}`}>
              <h4>{lang === "zh" ? r.zh : r.en} <span style={{ fontSize: 11, opacity: 0.6 }}>{r.date}</span></h4>
              <p>{lang === "zh" ? r.descZh : r.descEn}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="l-footer">
        <div><b>{t.credits}</b></div>
        <div>
          Sprout Lands © Cup Nooble · Cute Fantasy © Kenmi · Mystic Woods © Game Endeavor （{lang === "zh" ? "免费版授权，非商用" : "free tiers, non-commercial"}）
          · LPC crops (CC-BY-SA) · Kenney (CC0)
        </div>
        <div>
          {lang === "zh" ? "原始资产包不随仓库分发；本站为非商业作品集演示。" : "Raw packs are not redistributed in the repo; this site is a non-commercial portfolio demo."}
        </div>
        <div>
          新路谷物语 Newroad Valley · <a href="https://github.com/appleweiping/newroad-valley">appleweiping/pixel-ai-town</a> · 2026
        </div>
      </footer>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<Landing />);
