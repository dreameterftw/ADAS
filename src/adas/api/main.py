"""FastAPI application exposing live simulation state."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from adas.api.routes import assignments, benchmarks, hospitals, incidents, map_data, operations
from adas.app_state import init_simulation

LANDING_PAGE_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ADAS — Every minute, decided together</title>
    <meta
      name="description"
      content="Quantum-assisted ambulance dispatch, hospital matching, and traffic coordination for Indian cities."
    />
    <style>
      :root {
        --bg: #f4f1e8;
        --panel: #111827;
        --panel-2: #1b2437;
        --sand: #f5efe3;
        --ink: #111827;
        --muted: #5d6470;
        --green: #4aad8a;
        --green-soft: #def5eb;
        --amber: #df7d3d;
        --line: #e7e0d6;
        --card: rgba(255, 255, 255, 0.08);
      }
      * { box-sizing: border-box; }
      html { scroll-behavior: smooth; }
      body {
        margin: 0;
        font-family: Inter, "Segoe UI", sans-serif;
        background: var(--bg);
        color: var(--ink);
      }
      a { color: inherit; text-decoration: none; }
      .wrap { width: min(1180px, calc(100% - 40px)); margin: 0 auto; }
      .brand {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        font-weight: 700;
        font-size: 1.8rem;
        letter-spacing: -0.05em;
      }
      .brand-mark {
        width: 32px;
        height: 32px;
        border-radius: 8px;
        display: grid;
        place-items: center;
        background: var(--amber);
        color: white;
        font-size: 0.95rem;
      }
      .brand-dot { color: var(--amber); }
      .site-header {
        background: rgba(244, 241, 232, 0.93);
        backdrop-filter: blur(10px);
        border-bottom: 1px solid var(--line);
        position: sticky;
        top: 0;
        z-index: 10;
      }
      .nav {
        height: 86px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 24px;
      }
      .nav-links {
        display: flex;
        gap: 28px;
        margin-left: auto;
        margin-right: 18px;
        font-size: 0.78rem;
        color: var(--muted);
      }
      .nav-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 11px 16px;
        border-radius: 999px;
        background: var(--ink);
        color: white;
        font-size: 0.74rem;
      }
      .hero {
        position: relative;
        min-height: 640px;
        background: linear-gradient(120deg, rgba(17,24,39,0.92), rgba(17,24,39,0.38)),
          radial-gradient(circle at top left, rgba(255,255,255,0.22), transparent 30%),
          url('https://images.unsplash.com/photo-1584515933487-779824d29309?auto=format&fit=crop&w=1600&q=80') center/cover no-repeat;
        color: white;
        overflow: hidden;
      }
      .hero::before {
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(90deg, rgba(17,24,39,0.85) 0%, rgba(17,24,39,0.60) 35%, rgba(17,24,39,0.1) 100%);
      }
      .hero-content {
        position: relative;
        z-index: 1;
        padding: 86px 0 80px;
      }
      .eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-size: 0.7rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        opacity: 0.8;
      }
      .dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--amber);
        display: inline-block;
      }
      h1 {
        margin: 26px 0 0;
        font-size: clamp(3rem, 6vw, 5rem);
        line-height: 0.98;
        letter-spacing: -0.06em;
        max-width: 720px;
      }
      h1 span { color: rgba(255,255,255,0.7); }
      .hero p {
        margin-top: 22px;
        max-width: 620px;
        color: rgba(255,255,255,0.8);
        font-size: 1.02rem;
        line-height: 1.8;
      }
      .cta-row {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 28px;
      }
      .primary-btn, .secondary-btn {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        justify-content: center;
        border-radius: 999px;
        height: 48px;
        padding: 0 22px;
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 600;
      }
      .primary-btn {
        background: var(--amber);
        color: #fff;
      }
      .secondary-btn {
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.2);
        color: white;
      }
      .footer-tag {
        margin-top: 22px;
        font-size: 0.68rem;
        color: rgba(255,255,255,0.74);
        letter-spacing: 0.12em;
        text-transform: uppercase;
      }
      .hero-caption {
        position: absolute;
        right: 24px;
        left: 24px;
        bottom: 22px;
        z-index: 1;
        display: flex;
        justify-content: space-between;
        font-size: 0.64rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: rgba(255,255,255,0.72);
      }
      .context-band {
        border-bottom: 1px solid var(--line);
        background: var(--bg);
      }
      .context-inner {
        min-height: 78px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 20px;
        color: var(--muted);
        font-size: 0.7rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
      }
      .context-inner strong { color: var(--ink); }
      .problem-section {
        display: grid;
        grid-template-columns: 0.85fr 1.15fr;
        gap: 60px;
        padding: 80px 0 58px;
      }
      .problem-stat {
        padding-right: 42px;
        border-right: 1px solid var(--line);
      }
      .problem-stat .big {
        font-size: clamp(4rem, 7vw, 6rem);
        line-height: 1;
        margin-top: 18px;
        color: var(--amber);
        letter-spacing: -0.08em;
      }
      .problem-stat .big span { font-size: 0.45em; }
      .problem-stat p {
        margin-top: 10px;
        font-size: 0.9rem;
        line-height: 1.8;
        color: var(--muted);
      }
      .problem-copy h2 {
        margin: 0;
        font-size: clamp(2rem, 3vw, 3rem);
        line-height: 1.15;
        letter-spacing: -0.06em;
      }
      .problem-copy p {
        margin-top: 18px;
        color: var(--muted);
        font-size: 0.96rem;
        line-height: 1.85;
        max-width: 560px;
      }
      .section {
        border-top: 1px solid var(--line);
        padding: 74px 0;
      }
      .section-heading {
        display: flex;
        align-items: end;
        justify-content: space-between;
        gap: 18px;
        margin-bottom: 34px;
      }
      .section-heading h2 {
        margin: 0;
        font-size: clamp(2.2rem, 3vw, 3rem);
        letter-spacing: -0.06em;
        line-height: 1.1;
      }
      .section-heading p {
        color: var(--muted);
        line-height: 1.75;
        font-size: 0.92rem;
      }
      .steps-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 26px;
      }
      .step-card {
        background: rgba(255,255,255,0.3);
        border-radius: 18px;
        padding: 0;
        overflow: hidden;
        border: 1px solid rgba(17,24,39,0.06);
      }
      .step-media {
        height: 240px;
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(145deg, #dfe8f3, #f0e5d6);
      }
      .step-media::before {
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(135deg, rgba(17,24,39,0.06), transparent 60%);
      }
      .step-media .marker {
        position: absolute;
        top: 14px;
        left: 14px;
        padding: 6px 8px;
        background: rgba(255,255,255,0.72);
        border-radius: 8px;
        font-size: 0.66rem;
        font-weight: 700;
        letter-spacing: 0.08em;
      }
      .route-bg {
        width: 80%;
        height: 70%;
        position: relative;
      }
      .route-bg::before, .route-bg::after {
        content: "";
        position: absolute;
        border: 2px solid rgba(17,24,39,0.3);
      }
      .route-bg::before {
        inset: 10% 12% 12% 8%;
        border-right: none;
        border-bottom: none;
      }
      .route-bg::after {
        inset: auto 14% 20% 18%;
        height: 42%;
        border-left: none;
        border-top: none;
      }
      .route-line {
        position: absolute;
        left: 18%;
        top: 20%;
        width: 56%;
        height: 3px;
        background: linear-gradient(90deg, #ef8d35, #4aad8a);
        transform: rotate(20deg);
        border-radius: 10px;
      }
      .route-node {
        position: absolute;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: var(--green);
        box-shadow: 0 0 0 8px rgba(74,173,138,0.15);
      }
      .node-1 { left: 16%; top: 64%; }
      .node-2 { left: 50%; top: 42%; }
      .node-3 { right: 14%; top: 22%; }
      .step-body { padding: 18px 18px 15px; }
      .step-header {
        display: flex;
        align-items: center;
        gap: 10px;
        font-weight: 700;
        letter-spacing: -0.04em;
      }
      .step-body p {
        color: var(--muted);
        line-height: 1.8;
        font-size: 0.88rem;
        margin-top: 12px;
      }
      .step-footer { margin-top: 18px; padding-top: 12px; border-top: 1px solid var(--line); display: flex; justify-content: space-between; align-items: center; font-size: 0.62rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
      .confidence-card {
        background: var(--green-soft);
        color: var(--ink);
        padding: 22px 18px 18px;
        border-radius: 18px;
      }
      .confidence-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 0.68rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #296d5b;
      }
      .confidence-value {
        font-size: 4rem;
        line-height: 1;
        letter-spacing: -0.08em;
        margin-top: 14px;
        color: #1f6b5b;
      }
      .confidence-value span { font-size: 0.44em; }
      .confidence-card p { margin: 8px 0 10px; color: #3b5e56; }
      .confidence-track { height: 5px; background: rgba(31,107,91,0.15); border-radius: 999px; overflow: hidden; }
      .confidence-track span { display:block; width: 94%; height: 100%; background: linear-gradient(90deg, #2da57d, #4aad8a); }
      .confidence-meta {
        margin-top: 14px;
        display: grid;
        gap: 6px;
        font-size: 0.7rem;
        color: #2a5b50;
      }
      .quantum-band {
        background: #eef1ec;
        border-top: 1px solid var(--line);
        padding: 76px 0;
      }
      .quantum-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 54px;
        align-items: center;
      }
      .quantum-copy h2 { margin: 0; font-size: clamp(2.2rem, 3vw, 3rem); letter-spacing: -0.06em; }
      .quantum-copy p { color: var(--muted); line-height: 1.8; }
      .quantum-card {
        background: #f9fbf7;
        border: 1px solid rgba(17,24,39,0.06);
        border-radius: 18px;
        padding: 24px;
      }
      .method {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 16px;
        padding-top: 20px;
        border-top: 1px solid var(--line);
        margin-top: 18px;
      }
      .method-tag {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        min-width: 64px;
        height: 36px;
        background: rgba(113, 151, 126, 0.1);
        color: #234a38;
        font-size: 0.66rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }
      .method h3 { margin: 0 0 8px; }
      .method p { margin: 0; color: var(--muted); line-height: 1.72; }
      .route-panel {
        background: var(--panel);
        color: white;
        border-radius: 18px;
        padding: 22px;
      }
      .route-panel-head {
        display: flex;
        justify-content: space-between;
        font-size: 0.62rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: rgba(255,255,255,0.64);
      }
      .route-panel-head strong { color: white; }
      .map-wrap {
        margin-top: 24px;
        background: rgba(255,255,255,0.02);
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.08);
      }
      .map-wrap svg { display:block; width:100%; height:auto; }
      .route-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 44px;
        align-items: center;
        padding: 70px 0 0;
      }
      .route-grid img {
        width: 100%;
        border-radius: 18px;
        display: block;
      }
      .lane-card {
        background: rgba(255,255,255,0.18);
        border: 1px solid rgba(17,24,39,0.06);
        border-radius: 18px;
        padding: 22px;
      }
      .lane-card h3 { margin: 0 0 8px; }
      .lane-card p { margin: 0; color: var(--muted); line-height: 1.7; }
      .baseline-list {
        display: grid;
        gap: 12px;
        margin-top: 12px;
      }
      .baseline-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        border-bottom: 1px solid var(--line);
        padding: 12px 0;
        font-size: 0.86rem;
        color: var(--ink);
      }
      .baseline-item strong { font-weight: 600; }
      .baseline-item em {
        font-style: normal;
        font-size: 0.68rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
      }
      .closing-band {
        background: #eef1ec;
        border-top: 1px solid var(--line);
        border-bottom: 1px solid var(--line);
        padding: 54px 0;
      }
      .closing-inner {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
      }
      .closing-inner h2 {
        margin: 0;
        font-size: clamp(2.1rem, 3vw, 3rem);
        letter-spacing: -0.06em;
      }
      .footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 20px;
        padding: 26px 0 36px;
        color: var(--muted);
      }
      .footer p { margin: 0; }
      @media (max-width: 980px) {
        .problem-section, .quantum-grid, .route-grid, .steps-grid { grid-template-columns: 1fr; }
        .section-heading, .closing-inner { display: block; }
      }
      @media (max-width: 640px) {
        .nav-links { display: none; }
        .hero { min-height: 560px; }
        .hero-caption { display:none; }
        .context-inner { flex-wrap: wrap; padding: 18px 0; }
        .nav { height: 74px; }
        .brand { font-size: 1.55rem; }
      }
    </style>
  </head>
  <body>
    <header class="site-header">
      <nav class="wrap nav" aria-label="Main navigation">
        <a href="/" class="brand" aria-label="ADAS home">
          <span class="brand-mark">A</span>
          ADAS<span class="brand-dot">.</span>
        </a>
        <div class="nav-links">
          <a href="#how">How it works</a>
          <a href="#quantum">Why quantum</a>
          <a href="#research">Research</a>
          <a href="#evidence">Evidence</a>
        </div>
        <a class="nav-pill" href="/dashboard?demo=1">Open live dashboard →</a>
      </nav>
    </header>

    <main>
      <section class="hero" aria-labelledby="hero-title">
        <div class="wrap hero-content">
          <div class="eyebrow"><span class="dot"></span> Connected emergency response</div>
          <h1 id="hero-title">Every minute.<br />Every decision.<br /><span>Made together.</span></h1>
          <p>One ambulance. The right hospital. A clear route. ADAS connects the decisions that save time — when time matters most.</p>
          <div class="cta-row">
            <a class="primary-btn" href="/dashboard?demo=1">Start dispatch demo →</a>
            <a class="secondary-btn" href="#quantum">Why quantum →</a>
          </div>
          <div class="footer-tag">Built for the complexity of Indian cities</div>
        </div>
        <div class="hero-caption"><span>01 / The people behind the response</span><span>Every second counts →</span></div>
      </section>

      <div class="context-band">
        <div class="wrap context-inner">
          <span><strong>City-wide</strong> decision layer</span>
          <span>Ambulance dispatch / Hospital matching / Traffic coordination</span>
          <span>One connected plan</span>
        </div>
      </div>

      <section class="wrap problem-section">
        <div class="problem-stat">
          <div class="eyebrow"><span class="dot" style="background: var(--amber);"></span> The cost of waiting</div>
          <div class="big">7–10<span>%</span></div>
          <p>drop in survival per minute of delay in cardiac arrest</p>
        </div>
        <div class="problem-copy">
          <h2>In an emergency, disconnected decisions cost time.</h2>
          <p>A delayed dispatch. A congested intersection. A hospital with no available bed. In Indian cities, these aren’t separate problems — they’re part of the same response.</p>
          <p><strong>So we solve them together.</strong></p>
        </div>
      </section>

      <section class="wrap section" id="how">
        <div class="section-heading">
          <div>
            <div class="eyebrow" style="color: var(--muted);">How it works</div>
            <h2>Three decisions.<br />One better response.</h2>
          </div>
          <p>From the first call to the hospital door,<br />every part of the plan works in sync.</p>
        </div>

        <div class="steps-grid">
          <article class="step-card">
            <div class="step-media">
              <div class="marker">01</div>
              <div class="route-bg">
                <div class="route-line"></div>
                <span class="route-node node-1"></span>
                <span class="route-node node-2"></span>
                <span class="route-node node-3"></span>
              </div>
            </div>
            <div class="step-body">
              <div class="step-header">🚑 Who responds</div>
              <p>Match the right ambulance and hospital by severity, distance, specialty, and bed availability.</p>
              <div class="step-footer"><span>Dispatch + hospital matching</span><span>→</span></div>
            </div>
          </article>

          <article class="step-card">
            <div class="step-media">
              <div class="marker">02</div>
              <div class="route-bg" style="transform: rotate(8deg);">
                <div class="route-line" style="left: 12%; top: 40%; width: 62%; transform: rotate(10deg);"></div>
                <span class="route-node node-1" style="left: 18%; top: 70%;"></span>
                <span class="route-node node-2" style="left: 45%; top: 50%;"></span>
                <span class="route-node node-3" style="right: 14%; top: 25%;"></span>
              </div>
            </div>
            <div class="step-body">
              <div class="step-header">🛣️ How it gets there</div>
              <p>Coordinate traffic signals ahead of the ambulance and resolve competing routes before they become medical delays.</p>
              <div class="step-footer"><span>Routing + signal coordination</span><span>→</span></div>
            </div>
          </article>

          <article class="step-card">
            <div class="step-body" style="padding-bottom: 10px;">
              <div class="confidence-card">
                <div class="confidence-head"><span>Plan confidence</span> ✓</div>
                <div class="confidence-value">94<span>%</span></div>
                <p>Probability of arriving on time</p>
                <div class="confidence-track"><span></span></div>
                <div class="confidence-meta">
                  <span>✓ Bed confirmed</span>
                  <span>✓ Route and signals coordinated</span>
                </div>
              </div>
            </div>
            <div class="step-body">
              <div class="step-header">🛡️ How sure we are</div>
              <p>Go beyond a single ETA. A confidence score estimates whether the plan can meet the critical window and flags when it needs to change.</p>
              <div class="step-footer"><span>Live on-time confidence</span><span>→</span></div>
            </div>
          </article>
        </div>
      </section>

      <section class="quantum-band" id="quantum">
        <div class="wrap quantum-grid">
          <div class="quantum-copy">
            <div class="eyebrow" style="color: var(--muted);">Why quantum</div>
            <h2>Not a buzzword.<br />Two specific jobs.</h2>
            <p>Quantum-assisted where it helps. Classically benchmarked where it matters.</p>
            <div class="quantum-card">
              <div class="method">
                <span class="method-tag">QAOA</span>
                <div>
                  <h3>The decider</h3>
                  <p>Searches ambulance, hospital, and signal assignments as one connected optimization problem.</p>
                </div>
              </div>
              <div class="method">
                <span class="method-tag">QAE</span>
                <div>
                  <h3>The risk auditor</h3>
                  <p>Estimates the chance of arriving on time with fewer samples for the same precision.</p>
                </div>
              </div>
            </div>
          </div>

          <div class="route-panel">
            <div class="route-panel-head"><span><span class="dot" style="background: #7ee0b2;"></span> Connected response</span><strong>Illustrative plan</strong></div>
            <div class="map-wrap">
              <svg viewBox="0 0 520 340" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Illustrative route overview">
                <rect width="520" height="340" fill="#101827"/>
                <path d="M0 80H120V0M0 210H520M0 270H200V80H520M70 340V140H320V0M120 340V200M320 340V140M420 340V0M0 40H240V340" fill="none" stroke="#2d3d57" stroke-width="2"/>
                <path d="M70 270H120V200H240V140H320V80H420" fill="none" stroke="#8adfc2" stroke-width="5" stroke-dasharray="8 8"/>
                <circle cx="70" cy="270" r="8" fill="#8adfc2"/>
                <circle cx="420" cy="80" r="9" fill="#101827" stroke="#8adfc2" stroke-width="3"/>
                <circle cx="120" cy="200" r="5" fill="#f6f7f8"/>
                <circle cx="240" cy="140" r="5" fill="#f6f7f8"/>
                <circle cx="320" cy="80" r="5" fill="#f6f7f8"/>
                <text x="30" y="240" fill="#eaf0ff" font-size="12">Andheri East</text>
                <text x="260" y="50" fill="#eaf0ff" font-size="12">Sion Hospital</text>
              </svg>
            </div>
          </div>
        </div>
      </section>

      <section class="wrap section" id="research">
        <div class="section-heading">
          <div>
            <div class="eyebrow" style="color: var(--muted);">Research & real-world context</div>
            <h2>Built for real roads.<br />Grounded in real questions.</h2>
          </div>
          <p>Indian emergency response is the starting point.<br />Not an afterthought.</p>
        </div>

        <div class="route-grid">
          <img src="https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=1200&q=80" alt="Dense urban traffic" />
          <div class="lane-card">
            <div class="eyebrow" style="color: var(--muted);">01 / Travel-time variability</div>
            <h3>An average ETA isn’t the whole story.</h3>
            <p>Congestion changes through the day. A route that looks fast on average may still miss the critical window.</p>
            <div class="baseline-list">
              <div class="baseline-item"><strong>Fixed-time signal control</strong><em>Baseline</em></div>
              <div class="baseline-item"><strong>Closest-idle dispatch</strong><em>Baseline</em></div>
              <div class="baseline-item"><strong>Simulated annealing</strong><em>Baseline</em></div>
            </div>
          </div>
        </div>
      </section>

      <section class="wrap section" id="evidence">
        <div>
          <div class="eyebrow" style="color: var(--muted);">Evidence, not assumptions</div>
          <h2>We show our work.</h2>
          <p>Every method needs a fair comparison. ADAS is a research prototype, evaluated against classical approaches at matched problem sizes.</p>
        </div>
        <div class="lane-card">
          <div class="baseline-list">
            <div class="baseline-item"><strong>Fixed-time signals</strong><span>✓</span></div>
            <div class="baseline-item"><strong>Closest-idle dispatch</strong><span>✓</span></div>
            <div class="baseline-item"><strong>Simulated annealing</strong><span>✓</span></div>
            <div class="baseline-item"><strong>ADAS · QAOA + QAE</strong><span>✓</span></div>
          </div>
        </div>
      </section>

      <section class="closing-band">
        <div class="wrap closing-inner">
          <div>
            <div class="eyebrow" style="color: var(--muted);">Every minute, decided together</div>
            <h2>A connected city.<br />A coordinated response.</h2>
          </div>
          <a class="primary-btn" href="/dashboard?demo=1">Open live dashboard →</a>
        </div>
      </section>
    </main>

    <footer class="wrap footer">
      <a href="/" class="brand" aria-label="ADAS home">
        <span class="brand-mark">A</span>
        ADAS<span class="brand-dot">.</span>
      </a>
      <p>A decision layer for city-wide emergency response.</p>
      <span>ADAS © 2026</span>
    </footer>
  </body>
</html>
"""

LANING_PAGE_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ADAS Lane Plan</title>
    <style>
      :root {
        --bg: #f4f1e8;
        --ink: #111827;
        --muted: #5d6470;
        --panel: #0f172a;
        --panel-soft: #15253f;
        --green: #4aad8a;
        --green-soft: #e6f9f0;
        --amber: #df7d3d;
        --line: #e7e0d6;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: Inter, "Segoe UI", sans-serif;
        background: linear-gradient(180deg, #f8f6f2 0%, #f0efe9 100%);
        color: var(--ink);
      }
      a { text-decoration: none; color: inherit; }
      .wrap { width: min(1200px, calc(100% - 40px)); margin: 0 auto; }
      .topbar {
        height: 86px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        border-bottom: 1px solid var(--line);
        background: rgba(244, 241, 232, 0.95);
      }
      .brand { display: inline-flex; align-items: center; gap: 10px; font-weight: 800; letter-spacing: -0.06em; font-size: 1.7rem; }
      .brand-mark { width: 30px; height: 30px; background: var(--amber); color: white; border-radius: 8px; display: inline-grid; place-items: center; }
      .nav { display: flex; gap: 12px; color: var(--muted); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.12em; }
      .nav a { padding: 8px 12px; border-radius: 999px; }
      .nav a.active { background: #f7ecdf; color: var(--ink); }
      .page { padding: 32px 0 64px; }
      .header-row { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-bottom: 28px; }
      .eyebrow { font-size: 0.68rem; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); }
      h1 { margin: 10px 0 0; font-size: clamp(2.3rem, 4vw, 4rem); letter-spacing: -0.08em; }
      .status-pill { display: inline-flex; align-items: center; gap: 8px; background: var(--green-soft); color: #195f4a; border-radius: 999px; padding: 10px 16px; font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; font-weight: 700; }
      .dot { width: 8px; height: 8px; background: var(--green); border-radius: 50%; display: inline-block; }
      .grid { display: grid; grid-template-columns: 1.4fr 0.6fr; gap: 24px; }
      .panel { background: white; border: 1px solid var(--line); border-radius: 20px; overflow: hidden; }
      .map-panel { background: linear-gradient(180deg, #f7f3eb 0%, #f2efe8 100%); }
      .map-meta { padding: 18px 20px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--line); font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); }
      .map-box { padding: 20px; }
      .map-box svg { display: block; width: 100%; height: auto; background: rgba(17,24,39,0.02); border-radius: 16px; }
      .metrics { display: grid; gap: 18px; }
      .stat { background: #fff; border: 1px solid var(--line); border-radius: 18px; padding: 18px; }
      .stat-label { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); }
      .stat-value { margin-top: 10px; font-size: clamp(2rem, 3vw, 3rem); letter-spacing: -0.08em; font-weight: 700; }
      .stat-value span { font-size: 0.45em; }
      .stat-note { margin-top: 8px; line-height: 1.6; color: var(--muted); }
      .lane-list { margin-top: 24px; display: grid; gap: 14px; }
      .lane-item { display: flex; align-items: center; justify-content: space-between; gap: 12px; background: rgba(255,255,255,0.7); border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px; }
      .lane-main { display: flex; align-items: center; gap: 12px; }
      .lane-badge { width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center; background: var(--green-soft); color: #145943; font-weight: 700; }
      .lane-title { font-weight: 700; }
      .lane-meta { font-size: 0.76rem; color: var(--muted); }
      .lane-score { font-weight: 800; font-size: 1.15rem; }
      .lane-score.good { color: #1a6f54; }
      .lane-score.warn { color: var(--amber); }
      @media (max-width: 820px) { .grid { grid-template-columns: 1fr; } .header-row { display: block; } .nav { display:flex; gap:10px; flex-wrap:wrap; } }
    </style>
  </head>
  <body>
    <header class="topbar">
      <div class="wrap" style="display: flex; align-items: center; justify-content: space-between; width: min(1200px, calc(100% - 40px));">
        <a href="/" class="brand" aria-label="ADAS home"><span class="brand-mark">A</span>ADAS<span style="color: var(--amber);">.</span></a>
        <nav class="nav" aria-label="Page navigation"><a href="/">Overview</a><a href="/dashboard">Dashboard</a><a href="/laning" class="active">Lane plan</a><a href="/benchmarks">Benchmarks</a><a href="/driver">Driver</a><a href="/dashboard?demo=1#alerts">Alerts</a></nav>
      </div>
    </header>
    <main class="page"><div class="wrap"><div class="header-row"><div><div class="eyebrow">LANE PLAN · ILLUSTRATIVE</div><h1>Connected route overview</h1><p>Sample route and metrics for demonstration only; live dispatch data is shown on the dashboard.</p></div><div class="status-pill">Illustrative plan</div></div><div class="grid"><section class="panel map-panel"><div class="map-meta"><span>Sample route</span><strong>Andheri East → Sion Hospital</strong></div><div class="map-box"><svg viewBox="0 0 620 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Illustrative lane plan map"><rect width="620" height="420" fill="#f2eee7"/><g stroke="#d5d9df" stroke-width="2" fill="none"><path d="M0 90H130V0M0 220H620M0 280H195V90H620M65 420V150H330V0M120 420V220M330 420V150M420 420V0M0 46H230V420"/><path d="M65 280H120V220H240V150H330V90H420" stroke="#3b9f7c" stroke-width="6" stroke-dasharray="9 8"/></g><circle cx="65" cy="280" r="10" fill="#3b9f7c"/><circle cx="420" cy="90" r="10" fill="#111827" stroke="#3b9f7c" stroke-width="3"/><circle cx="120" cy="220" r="5" fill="#111827"/><circle cx="240" cy="150" r="5" fill="#111827"/><circle cx="330" cy="90" r="5" fill="#111827"/><text x="22" y="256" fill="#111827" font-size="12">Andheri East</text><text x="428" y="72" fill="#111827" font-size="12">Sion Hospital</text></svg></div></section><aside class="metrics"><div class="stat"><div class="stat-label">Sample ETA</div><div class="stat-value">12<span>m</span></div><div class="stat-note">Illustrative value, not a live estimate.</div></div><div class="stat"><div class="stat-label">Traffic stress</div><div class="stat-value">—</div><div class="stat-note">Live traffic data is not connected.</div></div></aside></div><div class="lane-list"><div class="lane-item"><div class="lane-main"><div class="lane-badge">A</div><div><div class="lane-title">Ambulance corridor</div><div class="lane-meta">Illustrative route only</div></div></div><div class="lane-score good">Sample</div></div><div class="lane-item"><div class="lane-main"><div class="lane-badge" style="background: #f7ecdf; color: var(--amber);">H</div><div><div class="lane-title">Hospital handoff</div><div class="lane-meta">Illustrative; bed status is not live</div></div></div><div class="lane-score good">Sample</div></div><div class="lane-item"><div class="lane-main"><div class="lane-badge" style="background: #fff2c2; color: #8a5a00;">S</div><div><div class="lane-title">Signal coordination</div><div class="lane-meta">Signal controls are not connected</div></div></div><div class="lane-score warn">Demo</div></div></div><p><a class="primary-btn" href="/dashboard?demo=1">View live dispatch →</a></p></div></main></body></html>
"""

DASHBOARD_PAGE_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ADAS Dashboard</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />
    <style>
      :root {
        --bg: #0f1115;
        --bg-2: #121923;
        --panel: #141a24;
        --panel-strong: #1b2431;
        --panel-soft: #1c2330;
        --line: rgba(255,255,255,0.08);
        --text: #edf4ff;
        --muted: #9aa8b9;
        --amber: #f0a745;
        --red: #f26464;
        --teal: #5fd3b2;
        --teal-soft: rgba(95,211,178,0.12);
        --danger-soft: rgba(242,100,100,0.12);
        --shadow: rgba(0,0,0,0.28);
      }
      * { box-sizing: border-box; }
      html, body { margin: 0; height: 100%; background: var(--bg); color: var(--text); font-family: Inter, Segoe UI, sans-serif; }
      body { min-height: 100vh; }
      a { color: inherit; text-decoration: none; }
      .topbar { height: 74px; border-bottom: 1px solid var(--line); background: rgba(15,17,21,0.9); position: sticky; top: 0; z-index: 12; }
      .wrap { width: min(1460px, calc(100% - 32px)); margin: 0 auto; }
      .nav { display: flex; align-items: center; height: 100%; gap: 22px; }
      .brand { display: inline-flex; align-items: center; gap: 10px; font-weight: 800; letter-spacing: -0.06em; }
      .brand-mark { width: 20px; height: 20px; background: var(--red); border-radius: 6px; display: inline-grid; place-items: center; font-size: 0.7rem; }
      .tabs { display: flex; gap: 20px; margin-left: 18px; }
      .tab { color: var(--muted); padding: 18px 0 14px; border-bottom: 2px solid transparent; font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; }
      .tab.active { color: var(--text); border-color: var(--teal); }
      .status-cluster { margin-left: auto; display: flex; align-items: center; gap: 14px; }
      .live { display: inline-flex; align-items: center; gap: 8px; color: var(--muted); font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase; }
      .pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--teal); box-shadow: 0 0 0 5px rgba(95,211,178,0.15); }
      .sim-time { color: var(--muted); font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase; }
      .decision-counter { color: var(--muted); font-size: 0.72rem; letter-spacing: 0.04em; }
      .ghost-btn { border: 1px solid var(--line); background: transparent; color: var(--text); border-radius: 10px; padding: 10px 14px; font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase; }
      .dashboard-body { display: grid; grid-template-columns: 1.7fr 0.9fr; min-height: calc(100vh - 74px); }
      .map-panel { position: relative; padding: 18px 16px 16px; border-right: 1px solid var(--line); background: linear-gradient(180deg, #0d1218 0%, #101923 100%); }
      .map-surface { position: relative; background: linear-gradient(180deg, #111c2a, #0e1720); border: 1px solid var(--line); border-radius: 20px; overflow: hidden; height: 100%; min-height: 720px; }
      .map-surface { min-height: 680px; }
      #live-map { position: absolute; inset: 0; z-index: 1; min-height: 680px; background: #0f1115; }
      .leaflet-container { background: #0f1115; font: inherit; }
      .leaflet-tile-pane { filter: invert(0.9) hue-rotate(180deg) brightness(0.72) contrast(1.12) saturate(0.55); }
      .leaflet-control-attribution { background: rgba(15,17,21,0.78) !important; color: #aab4c0 !important; }
      .leaflet-control-attribution a { color: #8bc9bd !important; }
      .leaflet-control-zoom a { background: #141a24 !important; color: var(--text) !important; border-color: var(--line) !important; }
      .map-marker { border: 0; background: transparent; }
      .marker-dot { display: block; width: 14px; height: 14px; border: 2px solid #f5f7fa; border-radius: 50%; box-shadow: 0 0 14px currentColor; }
      .marker-ambulance { color: var(--red); background: var(--red); animation: map-pulse 1.7s ease-out infinite; }
      .marker-incident { color: var(--amber); background: var(--amber); }
      .marker-hospital { color: var(--teal); background: var(--teal); border-radius: 3px; }
      @keyframes map-pulse { 0% { box-shadow: 0 0 0 0 rgba(242,100,100,0.62); } 100% { box-shadow: 0 0 0 14px rgba(242,100,100,0); } }
      .leaflet-overlay-pane path.dispatch-route { stroke-dasharray: 9 9; animation: route-flow 1.2s linear infinite; }
      @keyframes route-flow { to { stroke-dashoffset: -18; } }
      .map-legend { z-index: 500; pointer-events: none; }
      .map-loading { position: absolute; z-index: 3; right: 18px; bottom: 18px; border: 1px solid var(--line); border-radius: 8px; background: rgba(15,17,21,0.88); padding: 8px 10px; color: var(--muted); font-size: 0.68rem; }
      .map-legend { position: absolute; left: 22px; top: 18px; z-index: 2; background: rgba(18,25,35,0.8); border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; font-size: 0.68rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }
      .legend-row { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
      .legend-row:first-child { margin-top: 0; }
      .legend-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
      .sidebar { background: #121922; padding: 18px 18px 10px; overflow: auto; }
      .card { background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 16px; }
      .section-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
      .section-head h3 { margin: 0; font-size: 0.8rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); }
      .incident-list { display: grid; gap: 12px; }
      .incident-item { background: rgba(255,255,255,0.02); border: 1px solid var(--line); border-radius: 14px; padding: 12px 12px 10px; }
      .incident-header { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
      .severity { display: inline-flex; align-items: center; gap: 6px; border-radius: 999px; padding: 5px 8px; font-size: 0.62rem; letter-spacing: 0.08em; text-transform: uppercase; }
      .severity.high { background: var(--danger-soft); color: #ff9a9a; }
      .severity.medium { background: rgba(240,167,69,0.12); color: #f3c275; }
      .severity.low { background: rgba(95,211,178,0.12); color: #9fe8d1; }
      .incident-title { margin-top: 12px; font-size: 1.05rem; font-weight: 700; }
      .incident-meta { margin-top: 4px; color: var(--muted); font-size: 0.72rem; }
      .incident-footer { margin-top: 12px; display: grid; grid-template-columns: 1fr auto; gap: 8px; align-items: center; }
      .confidence-mini { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 0.7rem; }
      .ring { width: 36px; height: 36px; border-radius: 50%; background: conic-gradient(var(--teal) 0 88%, rgba(255,255,255,0.08) 0); display: grid; place-items: center; font-size: 0.6rem; font-weight: 700; color: var(--text); }
      .log-box { margin-top: 18px; background: #0b1016; border: 1px solid var(--line); border-radius: 14px; padding: 12px; font-family: "SFMono-Regular", Consolas, monospace; font-size: 0.68rem; line-height: 1.75; color: #dfeaf6; max-height: 220px; overflow: auto; }
      .log-line { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .detail-overlay { position: absolute; inset: 0; z-index: 600; display: flex; justify-content: flex-end; pointer-events: none; }
      .detail-panel { pointer-events: all; width: min(420px, 88%); background: rgba(17,21,29,0.96); border-left: 1px solid var(--line); box-shadow: -18px 0 42px rgba(0,0,0,0.38); padding: 18px 20px; }
      .detail-top { display: flex; justify-content: space-between; align-items: center; }
      .detail-top h2 { margin: 0; font-size: 1.25rem; }
      .close-btn { border: 1px solid var(--line); border-radius: 8px; padding: 8px 10px; color: var(--muted); background: transparent; }
      .big-ring { width: 110px; height: 110px; margin: 18px auto 8px; background: conic-gradient(var(--teal) 0 94%, rgba(255,255,255,0.08) 0); border-radius: 50%; display: grid; place-items: center; font-size: 1.45rem; font-weight: 800; }
      .detail-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 12px; margin-top: 14px; }
      .mini-stat { border: 1px solid var(--line); background: rgba(255,255,255,0.02); border-radius: 12px; padding: 12px; }
      .mini-stat .label { font-size: 0.62rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; }
      .mini-stat .value { margin-top: 8px; font-size: 0.96rem; font-weight: 700; }
      .tag-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 18px; }
      .tag { padding: 7px 10px; border-radius: 999px; background: rgba(255,255,255,0.05); border: 1px solid var(--line); font-size: 0.68rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
      .tag.teal { color: #a9ead5; background: rgba(95,211,178,0.08); }
      .whatif { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 18px; }
      .whatif button { border: 1px solid var(--line); background: rgba(255,255,255,0.02); color: var(--text); border-radius: 999px; padding: 8px 10px; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.08em; }
      .tab { display: block; color: var(--muted); text-decoration: none; }
      .tab.active { color: var(--text); }
      .map-loading::before { content: ""; display: inline-block; width: 9px; height: 9px; margin-right: 8px; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; vertical-align: -1px; animation: feed-spin 0.8s linear infinite; }
      .map-loading.connected::before { display: none; }
      .map-loading.error { color: #ff9a9a; }
      .map-loading.error::before { border-right-color: currentColor; animation: none; }
      .live.disconnected .pulse { background: var(--red); box-shadow: 0 0 0 5px rgba(242,100,100,0.15); }
      @keyframes feed-spin { to { transform: rotate(360deg); } }
      @media (prefers-reduced-motion: reduce) { .map-loading::before { animation-duration: 2s; } }
      @media (max-width: 1100px) { .dashboard-body { grid-template-columns: 1fr; } .map-panel { min-height: 580px; } .sidebar { border-top: 1px solid var(--line); } }
      @media (max-width: 760px) {
        .topbar { height: auto; min-height: 74px; }
        .nav { height: auto; min-height: 74px; flex-wrap: wrap; gap: 10px 14px; padding: 12px 0; }
        .tabs { order: 3; width: 100%; margin: 0; justify-content: space-between; gap: 10px; }
        .status-cluster { gap: 8px; }
        .map-surface { min-height: 500px; }
        #live-map { min-height: 500px; }
      }
      @media (max-width: 420px) {
        .nav { gap: 10px; }
        .status-cluster { font-size: 0.62rem; }
        .decision-counter { display: none; }
        .ghost-btn { padding: 8px 10px; font-size: 0.62rem; }
        .tab { font-size: 0.64rem; letter-spacing: 0.04em; }
        .map-panel { padding: 10px 8px; }
        .detail-panel { width: min(360px, 94%); padding: 14px; }
      }
    </style>
  </head>
  <body>
    <header class="topbar"><div class="wrap nav"><a href="/" class="brand" aria-label="ADAS home"><span class="brand-mark">A</span>ADAS</a><nav class="tabs" aria-label="Dashboard pages"><a class="tab active" href="/dashboard" aria-current="page">Map</a><a class="tab" href="/laning">Lane plan</a><a class="tab" href="/benchmarks">Benchmarks</a><a class="tab" href="/driver">Driver</a></nav><div class="status-cluster"><div class="live" id="connection-status" role="status"><span class="pulse"></span> Connecting</div><div class="sim-time" id="sim-time">T+00:00</div><div class="decision-counter" id="decision-counter">Decisions loading</div></div><button class="ghost-btn" id="reset-demo">Reset demo</button></div></header>
    <main class="dashboard-body">
      <section class="map-panel">
        <div class="map-surface">
          <div id="live-map" role="application" aria-label="Live ambulance dispatch map"></div>
          <div class="map-legend"><div>Legend</div><div class="legend-row"><span class="legend-dot" style="background: var(--red);"></span> Ambulance</div><div class="legend-row"><span class="legend-dot" style="background: var(--amber);"></span> Incident</div><div class="legend-row"><span class="legend-dot" style="background: var(--teal);"></span> Hospital</div></div>
          <div class="map-loading" id="map-status" role="status" aria-live="polite">Connecting to dispatch feed...</div>
        </div>
        <div class="detail-overlay">
          <aside class="detail-panel" id="incident-detail">
            <div class="detail-top"><h2 id="detail-title">Select an incident</h2><button class="close-btn" id="close-detail">Close</button></div>
            <div class="detail-grid">
              <div class="mini-stat"><div class="label">Severity</div><div class="value" id="detail-severity">—</div></div>
              <div class="mini-stat"><div class="label">Ambulance</div><div class="value" id="detail-ambulance">—</div></div>
              <div class="mini-stat"><div class="label">Hospital</div><div class="value" id="detail-hospital">—</div></div>
              <div class="mini-stat"><div class="label">Travel time</div><div class="value" id="detail-eta">—</div></div>
            </div>
            <div class="tag-row"><span class="tag teal" id="detail-match">Awaiting assignment</span></div>
          </aside>
        </div>
      </section>

      <aside class="sidebar">
        <div class="section-head" id="alerts"><h3>Active incidents</h3><span style="color: var(--muted);" id="incident-count">0</span></div>
        <div class="incident-list" id="incident-list"></div>
        <div class="section-head" style="margin-top: 18px;"><h3>Solver log</h3></div>
        <div class="log-box">
          <div class="log-line" id="solver-log">Dispatch feed will appear here.</div>
        </div>
      </aside>
    </main>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
    <script>
      const map = L.map('live-map', { zoomControl: false }).setView([19.12, 72.86], 12);
      L.control.zoom({ position: 'topright' }).addTo(map);
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19
      }).addTo(map);
      const markerLayer = L.layerGroup().addTo(map);
      const routeLayer = L.layerGroup().addTo(map);
      const markerIcons = {
        ambulance: L.divIcon({ className: 'map-marker', html: '<span class="marker-dot marker-ambulance"></span>', iconSize: [16, 16], iconAnchor: [8, 8] }),
        incident: L.divIcon({ className: 'map-marker', html: '<span class="marker-dot marker-incident"></span>', iconSize: [14, 14], iconAnchor: [7, 7] }),
        hospital: L.divIcon({ className: 'map-marker', html: '<span class="marker-dot marker-hospital"></span>', iconSize: [14, 14], iconAnchor: [7, 7] })
      };
      let selectedIncidentId = null;
      let refreshInProgress = false;
      let lastFeedError = '';

      async function requestJson(url, options = {}) {
        const response = await fetch(url, { ...options, cache: 'no-store' });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
        return payload;
      }

      function severityName(value) {
        if (value >= 5) return 'Critical';
        if (value >= 4) return 'High';
        if (value >= 3) return 'Medium';
        return 'Low';
      }

      function addMarker(entity, type, label, onClick) {
        if (!entity.position) return;
        const marker = L.marker([entity.position.lat, entity.position.lon], { icon: markerIcons[type], title: label })
          .bindTooltip(label, { direction: 'top', offset: [0, -8] });
        if (onClick) marker.on('click', onClick);
        marker.addTo(markerLayer);
      }

      function selectIncident(incident, assignment, reveal = true) {
        selectedIncidentId = incident.id;
        if (reveal) document.getElementById('incident-detail').hidden = false;
        document.getElementById('detail-title').textContent = `Incident #${incident.id}`;
        document.getElementById('detail-severity').textContent = severityName(incident.severity);
        document.getElementById('detail-ambulance').textContent = assignment ? `Amb ${assignment.ambulance_id}` : 'Unassigned';
        document.getElementById('detail-hospital').textContent = assignment?.hospital_id == null ? 'No match' : `Hospital ${assignment.hospital_id}`;
        document.getElementById('detail-eta').textContent = assignment ? `${Math.ceil(assignment.travel_time_sec / 60)} min` : '—';
        document.getElementById('detail-match').textContent = assignment?.hospital_match_reason?.replaceAll('_', ' ') || 'Awaiting assignment';
        const position = incident.position;
        if (position) map.flyTo([position.lat, position.lon], Math.max(map.getZoom(), 13), { duration: 0.5 });
        document.querySelectorAll('.incident-item').forEach((item) => item.classList.toggle('selected', Number(item.dataset.incidentId) === incident.id));
      }

      function renderIncidents(data) {
        const list = document.getElementById('incident-list');
        const assignments = new Map(data.routes.map((route) => [route.incident_id, route]));
        list.replaceChildren();
        document.getElementById('incident-count').textContent = data.incidents.length;
        data.incidents.forEach((incident) => {
          const assignment = assignments.get(incident.id);
          const article = document.createElement('article');
          article.className = 'incident-item';
          article.dataset.incidentId = incident.id;
          article.tabIndex = 0;
          const header = document.createElement('div');
          header.className = 'incident-header';
          const severity = document.createElement('span');
          severity.className = `severity ${incident.severity >= 4 ? 'high' : incident.severity === 3 ? 'medium' : 'low'}`;
          severity.textContent = severityName(incident.severity);
          const ambulance = document.createElement('span');
          ambulance.style.cssText = 'color: var(--muted); font-size:0.72rem;';
          ambulance.textContent = assignment ? `Amb ${assignment.ambulance_id}` : 'Unassigned';
          header.append(severity, ambulance);
          const title = document.createElement('div');
          title.className = 'incident-title';
          title.textContent = `Incident #${incident.id}`;
          const meta = document.createElement('div');
          meta.className = 'incident-meta';
          meta.textContent = assignment?.hospital_id == null ? 'Hospital match pending' : `Assigned hospital: ${assignment.hospital_id}`;
          const footer = document.createElement('div');
          footer.className = 'incident-footer';
          const travel = document.createElement('span');
          travel.style.cssText = 'color: var(--muted); font-size:0.7rem;';
          travel.textContent = assignment ? `ETA ${Math.ceil(assignment.travel_time_sec / 60)}m` : 'ETA pending';
          footer.append(document.createElement('span'), travel);
          article.append(header, title, meta, footer);
          article.addEventListener('click', () => selectIncident(incident, assignment));
          article.addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') selectIncident(incident, assignment); });
          list.append(article);
        });
        if (selectedIncidentId != null) {
          const selected = data.incidents.find((incident) => incident.id === selectedIncidentId);
          if (!selected) selectedIncidentId = null;
          else selectIncident(selected, assignments.get(selected.id), false);
        }
        if (selectedIncidentId == null && data.incidents.length) selectIncident(data.incidents[0], assignments.get(data.incidents[0].id));
        if (!data.incidents.length) {
          const panel = document.getElementById('incident-detail');
          panel.hidden = false;
          document.getElementById('detail-title').textContent = 'No active incident';
          document.getElementById('detail-severity').textContent = '—';
          document.getElementById('detail-ambulance').textContent = '—';
          document.getElementById('detail-hospital').textContent = '—';
          document.getElementById('detail-eta').textContent = '—';
          document.getElementById('detail-match').textContent = 'No active assignment';
        }
      }

      async function refreshMap() {
        if (refreshInProgress) return;
        refreshInProgress = true;
        const status = document.getElementById('map-status');
        try {
          await requestJson('/map/state');
          await requestJson('/incidents/tick?dt_seconds=30', { method: 'POST' });
          await requestJson('/assignments/replan', { method: 'POST' });
          const data = await requestJson('/map/state');
          const decisions = await requestJson('/benchmarks/decisions');
          markerLayer.clearLayers();
          routeLayer.clearLayers();
          data.hospitals.forEach((hospital) => addMarker(hospital, 'hospital', `Hospital ${hospital.id}`));
          data.ambulances.forEach((ambulance) => addMarker(ambulance, 'ambulance', `Ambulance ${ambulance.id}${ambulance.available ? ' · idle' : ' · assigned'}`));
          data.incidents.forEach((incident) => addMarker(
            incident,
            'incident',
            `Incident #${incident.id} · ${severityName(incident.severity)}`,
            () => selectIncident(incident, data.routes.find((route) => route.incident_id === incident.id))
          ));
          data.routes.forEach((route) => {
            if (route.path.length > 1) {
              L.polyline(route.path.map((point) => [point.lat, point.lon]), { color: '#5fd3b2', weight: 4, opacity: 0.9, className: 'dispatch-route' }).addTo(routeLayer);
            }
          });
          status.classList.remove('error');
          status.classList.add('connected');
          status.hidden = false;
          if (data.incidents.length && data.incidents.every((incident) => !incident.position)) {
            status.textContent = 'Graph coordinates unavailable for this scenario';
          } else {
            status.textContent = `${data.incidents.length} active · ${data.routes.length} routes`;
            if (!map.userHasMoved) {
              const positions = [...data.hospitals, ...data.ambulances, ...data.incidents].filter((entity) => entity.position).map((entity) => [entity.position.lat, entity.position.lon]);
              if (positions.length) map.fitBounds(positions, { padding: [40, 40], maxZoom: 14 });
              map.userHasMoved = true;
            }
          }
          const connection = document.getElementById('connection-status');
          connection.classList.remove('disconnected');
          connection.lastChild.textContent = ' Connected';
          document.getElementById('decision-counter').textContent = `QAOA ${decisions.qaoa} · fallback ${decisions.fallback}`;
          const totalSeconds = Math.floor(data.current_time);
          document.getElementById('sim-time').textContent = `T+${String(Math.floor(totalSeconds / 3600)).padStart(2, '0')}:${String(Math.floor(totalSeconds % 3600 / 60)).padStart(2, '0')}`;
          renderIncidents(data);
          document.getElementById('solver-log').textContent = `${data.routes.length} active dispatch route${data.routes.length === 1 ? '' : 's'} · simulation ${Math.floor(totalSeconds / 60)} min`;
          lastFeedError = '';
        } catch (error) {
          status.textContent = error.message || 'Dispatch feed unavailable';
          status.classList.remove('connected');
          status.classList.add('error');
          const connection = document.getElementById('connection-status');
          connection.classList.add('disconnected');
          connection.lastChild.textContent = ' Disconnected';
          if (lastFeedError !== status.textContent) console.error(error);
          lastFeedError = status.textContent;
        } finally {
          refreshInProgress = false;
        }
      }

      document.getElementById('close-detail').addEventListener('click', () => {
        document.getElementById('incident-detail').hidden = true;
      });
      document.getElementById('reset-demo').addEventListener('click', async () => {
        try {
          await requestJson('/demo/reset', { method: 'POST' });
        } catch (error) {
          document.getElementById('map-status').textContent = error.message || 'Unable to reset simulation';
          return;
        }
        selectedIncidentId = null;
        map.userHasMoved = false;
        document.getElementById('incident-detail').hidden = false;
        await refreshMap();
      });
      if (window.location.hash === '#alerts') {
        window.requestAnimationFrame(() => document.getElementById('alerts').scrollIntoView());
      }
      map.on('dragstart', () => { map.userHasMoved = true; });
      async function startDashboard() {
        if (new URLSearchParams(window.location.search).get('demo') === '1') {
          try {
            await requestJson('/incidents/demo/scenario', { method: 'POST' });
          } catch (error) {
            const status = document.getElementById('map-status');
            status.textContent = error.message || 'Unable to load the demo scenario.';
            status.classList.add('error');
            document.getElementById('connection-status').lastChild.textContent = ' Disconnected';
            document.getElementById('connection-status').classList.add('disconnected');
            console.error(error);
            return;
          }
        }
        await refreshMap();
      }
      startDashboard();
      window.setInterval(refreshMap, 8000);
    </script>
  </body>
</html>
"""

DRIVER_PAGE_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ADAS Driver</title>
    <style>
      :root {
        --bg: #0e1116;
        --panel: #111924;
        --panel-2: #192532;
        --line: rgba(255,255,255,0.08);
        --text: #eef7ff;
        --muted: #9aa9b8;
        --red: #f26464;
        --amber: #f0a745;
        --teal: #5fd3b2;
      }
      * { box-sizing: border-box; }
      body { margin: 0; min-height: 100vh; font-family: Inter, Segoe UI, sans-serif; background: var(--bg); color: var(--text); }
      .app { width: min(440px, calc(100% - 24px)); margin: 0 auto; min-height: 100vh; padding: 18px 0 28px; }
      .status-bar { display: flex; justify-content: space-between; align-items: center; padding: 8px 2px 18px; }
      .badge { display: inline-flex; align-items: center; gap: 8px; border-radius: 999px; padding: 7px 10px; background: rgba(95,211,178,0.12); color: #b9f0df; font-size: 0.68rem; letter-spacing: 0.12em; text-transform: uppercase; }
      .badge::before { content: ""; width: 8px; height: 8px; background: var(--teal); border-radius: 50%; }
      .confidence { display: flex; align-items: end; gap: 8px; }
      .confidence strong { font-size: clamp(2.2rem, 6vw, 3.1rem); letter-spacing: -0.08em; }
      .confidence span { color: var(--muted); font-size: 0.9rem; }
      .driver-nav { display: flex; gap: 14px; margin-bottom: 18px; font-size: 0.8rem; }
      .driver-nav a { color: var(--muted); }
      .map-card { background: linear-gradient(180deg, #101a23 0%, #152130 100%); border: 1px solid var(--line); border-radius: 22px; padding: 14px; }
      .map-box { position: relative; height: 240px; overflow: hidden; border-radius: 18px; background: #0c141c; }
      .map-box svg { display: block; width: 100%; height: 100%; }
      .info-stack { margin-top: 20px; display: grid; gap: 12px; }
      .info-row { display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 14px 16px; background: rgba(255,255,255,0.02); border: 1px solid var(--line); border-radius: 14px; }
      .label { color: var(--muted); font-size: 0.72rem; letter-spacing: 0.12em; text-transform: uppercase; }
      .value { font-weight: 700; }
      .cta { margin-top: 22px; width: 100%; border: none; border-radius: 16px; height: 60px; background: linear-gradient(90deg, #fa7b4d, #ed5b52); color: white; font-size: 0.82rem; letter-spacing: 0.14em; text-transform: uppercase; font-weight: 800; }
      .cta:disabled { cursor: not-allowed; opacity: 0.55; }
      .driver-message { min-height: 1.5em; color: var(--muted); font-size: 0.82rem; }
      @media (max-width: 420px) { .app { width: calc(100% - 16px); } }
    </style>
  </head>
  <body>
    <div class="app">
      <nav class="driver-nav" aria-label="Page navigation"><a href="/">Overview</a><a href="/dashboard">Dashboard</a><a href="/benchmarks">Benchmarks</a></nav>
      <div class="status-bar">
        <div class="badge" id="driver-status">Connecting</div>
        <div class="confidence"><strong id="driver-incident">—</strong><span>incident</span></div>
      </div>

      <div class="map-card">
        <div class="map-box">
          <svg viewBox="0 0 360 220" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Route map for driver view">
            <rect width="360" height="220" fill="#0c141c"/>
            <g stroke="#223449" stroke-width="2" fill="none">
              <path d="M0 110H110V30H260V170H360M40 220V140H160V50H300V220M120 220V100M270 220V60"/>
            </g>
            <polyline id="driver-route" stroke="#5fd3b2" stroke-width="5" stroke-dasharray="6 6" fill="none"/>
            <circle id="driver-start" r="8" fill="#f26464" hidden/>
            <circle id="driver-end" r="10" fill="#0e1116" stroke="#5fd3b2" stroke-width="3" hidden/>
          </svg>
        </div>
      </div>

      <div class="info-stack">
        <div class="info-row"><span class="label">Severity</span><span class="value" id="driver-severity">—</span></div>
        <div class="info-row"><span class="label">Ambulance</span><span class="value" id="driver-ambulance">—</span></div>
        <div class="info-row"><span class="label">Hospital</span><span class="value" id="driver-hospital">—</span></div>
        <div class="info-row"><span class="label">ETA</span><span class="value" id="driver-eta">—</span></div>
      </div>

      <button class="cta" id="confirm-arrival" disabled>Confirm arrival</button>
      <p class="driver-message" id="driver-message" role="status" aria-live="polite">Loading current dispatch…</p>
    </div>
    <script>
      async function requestJson(url, options = {}) {
        const response = await fetch(url, { ...options, cache: 'no-store' });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
        return payload;
      }

      async function loadDriverAssignment() {
        const message = document.getElementById('driver-message');
        const button = document.getElementById('confirm-arrival');
        try {
          const data = await requestJson('/map/state');
          const incident = data.incidents[0];
          const assignment = incident && data.routes.find((route) => route.incident_id === incident.id);
          if (!incident) {
            document.getElementById('driver-status').textContent = 'No active call';
            message.textContent = 'There are no active incidents in the simulation.';
            return;
          }

          document.getElementById('driver-incident').textContent = `#${incident.id}`;
          document.getElementById('driver-severity').textContent = incident.severity >= 5 ? 'Critical' : incident.severity >= 4 ? 'High' : incident.severity === 3 ? 'Medium' : 'Low';
          document.getElementById('driver-ambulance').textContent = assignment ? `Amb ${assignment.ambulance_id}` : 'Unassigned';
          document.getElementById('driver-hospital').textContent = assignment?.hospital_id == null ? 'No match' : `Hospital ${assignment.hospital_id}`;
          document.getElementById('driver-eta').textContent = assignment ? `${Math.ceil(assignment.travel_time_sec / 60)} min` : '—';
          document.getElementById('driver-status').textContent = assignment ? 'EN ROUTE' : 'Unassigned';

          if (assignment?.path?.length) {
            const lats = assignment.path.map((point) => point.lat);
            const lons = assignment.path.map((point) => point.lon);
            const minLat = Math.min(...lats), maxLat = Math.max(...lats);
            const minLon = Math.min(...lons), maxLon = Math.max(...lons);
            const project = (point) => {
              const x = 24 + (maxLon === minLon ? 0.5 : (point.lon - minLon) / (maxLon - minLon)) * 312;
              const y = 24 + (maxLat === minLat ? 0.5 : (maxLat - point.lat) / (maxLat - minLat)) * 172;
              return `${x},${y}`;
            };
            document.getElementById('driver-route').setAttribute('points', assignment.path.map(project).join(' '));
            const first = assignment.path[0], last = assignment.path[assignment.path.length - 1];
            const [startX, startY] = project(first).split(',');
            const [endX, endY] = project(last).split(',');
            document.getElementById('driver-start').setAttribute('cx', startX);
            document.getElementById('driver-start').setAttribute('cy', startY);
            document.getElementById('driver-start').hidden = false;
            document.getElementById('driver-end').setAttribute('cx', endX);
            document.getElementById('driver-end').setAttribute('cy', endY);
            document.getElementById('driver-end').hidden = false;
          }

          if (assignment) {
            button.dataset.incidentId = incident.id;
            button.dataset.ambulanceId = assignment.ambulance_id;
            button.disabled = false;
            message.textContent = 'Current assignment loaded from the dispatch feed.';
          } else {
            message.textContent = 'Waiting for an ambulance assignment.';
          }
        } catch (error) {
          document.getElementById('driver-status').textContent = 'Feed unavailable';
          message.textContent = error.message || 'Unable to load the current dispatch.';
        }
      }

      document.getElementById('confirm-arrival').addEventListener('click', async (event) => {
        const button = event.currentTarget;
        button.disabled = true;
        button.textContent = 'Recording…';
        try {
          const params = new URLSearchParams({ ambulance_id: button.dataset.ambulanceId });
          const result = await requestJson(`/incidents/${button.dataset.incidentId}/resolve?${params}`, { method: 'POST' });
          document.getElementById('driver-status').textContent = 'Resolved';
          document.getElementById('driver-message').textContent = `Arrival confirmed for incident #${result.incident_id}.`;
          button.textContent = 'Arrival confirmed';
        } catch (error) {
          document.getElementById('driver-message').textContent = error.message || 'Unable to confirm arrival.';
          button.textContent = 'Confirm arrival';
          button.disabled = false;
        }
      });

      loadDriverAssignment();
    </script>
  </body>
</html>
"""

BENCHMARKS_PAGE_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ADAS Benchmarks</title>
    <style>
      :root { --bg: #0f1115; --panel: #141a24; --line: rgba(255,255,255,0.1); --text: #edf4ff; --muted: #9aa8b9; --teal: #5fd3b2; --red: #f26464; }
      * { box-sizing: border-box; }
      body { margin: 0; min-height: 100vh; background: var(--bg); color: var(--text); font: 16px Inter, Segoe UI, sans-serif; }
      a { color: inherit; text-decoration: none; }
      .wrap { width: min(1000px, calc(100% - 32px)); margin: 0 auto; }
      header { border-bottom: 1px solid var(--line); }
      nav { min-height: 72px; display: flex; align-items: center; gap: 22px; flex-wrap: wrap; }
      .brand { font-weight: 800; margin-right: auto; }
      .nav-link { color: var(--muted); }
      main { padding: 48px 0; }
      h1 { margin: 0 0 8px; font-size: clamp(2rem, 5vw, 3rem); }
      .muted { color: var(--muted); }
      .card { margin-top: 22px; padding: 22px; border: 1px solid var(--line); border-radius: 16px; background: var(--panel); }
      .counts { display: flex; gap: 28px; flex-wrap: wrap; font-size: 1.2rem; }
      .actions { display: flex; gap: 10px; flex-wrap: wrap; margin: 14px 0; }
      button { border: 1px solid var(--line); border-radius: 8px; padding: 10px 14px; background: #202b38; color: var(--text); font: inherit; cursor: pointer; }
      button:disabled { cursor: wait; opacity: 0.6; }
      pre { max-height: 440px; overflow: auto; padding: 16px; border-radius: 10px; background: #090c10; color: #c7eadc; white-space: pre-wrap; overflow-wrap: anywhere; }
      @media (max-width: 560px) { nav { gap: 14px; padding: 14px 0; } .brand { width: 100%; } main { padding-top: 32px; } }
    </style>
  </head>
  <body>
    <header><nav class="wrap" aria-label="Page navigation"><a class="brand" href="/">ADAS</a><a class="nav-link" href="/dashboard">Map</a><a class="nav-link" href="/laning">Lane plan</a><a class="nav-link" href="/driver">Driver</a></nav></header>
    <main class="wrap">
      <h1>Solver benchmarks</h1>
      <p class="muted">Decision counts are from the current in-memory run. Detailed benchmark requests may take time on first load.</p>
      <section class="card" aria-labelledby="counts-title">
        <h2 id="counts-title">Solver decisions</h2>
        <div class="counts" id="decision-counts" role="status" aria-live="polite">Loading decision counts…</div>
      </section>
      <section class="card" aria-labelledby="data-title">
        <h2 id="data-title">Detailed results</h2>
        <p class="muted">These routes return simulator measurements, not production performance guarantees.</p>
        <div class="actions">
          <button type="button" data-endpoint="/benchmarks/scaling/preview">Load quick scaling results (n=2–3)</button>
          <button type="button" data-endpoint="/benchmarks/qae-efficiency">Load QAE efficiency results</button>
        </div>
        <p class="muted" id="benchmark-status" role="status" aria-live="polite">Choose a result set to load.</p>
        <pre id="benchmark-results" hidden></pre>
      </section>
    </main>
    <script>
      async function requestJson(url) {
        const response = await fetch(url, { cache: 'no-store' });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
        return payload;
      }

      async function loadDecisionCounts() {
        const target = document.getElementById('decision-counts');
        try {
          const counts = await requestJson('/benchmarks/decisions');
          target.textContent = `QAOA ${counts.qaoa} · classical fallback ${counts.fallback}`;
        } catch (error) {
          target.textContent = error.message || 'Decision counts unavailable.';
        }
      }

      document.querySelectorAll('[data-endpoint]').forEach((button) => {
        button.addEventListener('click', async () => {
          const status = document.getElementById('benchmark-status');
          const results = document.getElementById('benchmark-results');
          button.disabled = true;
          status.textContent = 'Loading benchmark results…';
          results.hidden = true;
          try {
            const data = await requestJson(button.dataset.endpoint);
            results.textContent = JSON.stringify(data, null, 2);
            results.hidden = false;
            status.textContent = `${data.length} result rows loaded.`;
          } catch (error) {
            status.textContent = error.message || 'Benchmark results unavailable.';
          } finally {
            button.disabled = false;
          }
        });
      });

      loadDecisionCounts();
    </script>
  </body>
</html>
"""

DOCS_PAGE_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ADAS Docs</title>
    <style>
      :root {
        --bg: #f6f4f0;
        --panel: #fff;
        --line: #e6dfd5;
        --ink: #101827;
        --muted: #5f6874;
        --red: #df5b43;
        --teal: #1d8f7d;
      }
      * { box-sizing: border-box; }
      body { margin: 0; font-family: Inter, Segoe UI, sans-serif; background: var(--bg); color: var(--ink); }
      .layout { display: grid; grid-template-columns: minmax(220px, 300px) minmax(0, 1fr); min-height: 100vh; }
      .toc { position: sticky; top: 0; align-self: start; height: 100vh; padding: 32px 20px; border-right: 1px solid var(--line); background: rgba(255,255,255,0.4); }
      .toc a { display: block; color: var(--muted); text-decoration: none; padding: 8px 10px; border-radius: 8px; margin-bottom: 8px; }
      .toc a.active { background: rgba(223,91,67,0.08); color: var(--ink); font-weight: 700; }
      .content { padding: 44px 28px 80px; }
      .content h1 { font-size: clamp(2.1rem, 4vw, 3.3rem); letter-spacing: -0.08em; margin-bottom: 20px; }
      .content h2 { margin-top: 36px; font-size: clamp(1.4rem, 2.4vw, 2rem); letter-spacing: -0.05em; }
      .content p, .content li { color: var(--muted); line-height: 1.8; font-size: 1rem; }
      .content .box { background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 18px 20px; margin-top: 18px; }
      code { background: rgba(16,24,39,0.05); border-radius: 8px; padding: 0.15rem 0.45rem; }
      @media (max-width: 860px) { .layout { grid-template-columns: 1fr; } .toc { position: relative; height: auto; border-right: none; border-bottom: 1px solid var(--line); } }
    </style>
  </head>
  <body>
    <div class="layout">
      <aside class="toc">
        <div style="font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); margin-bottom: 18px;">ADAS Docs</div>
        <a href="/">Landing page</a>
        <a href="/dashboard">Dashboard</a>
        <a href="/laning">Lane plan</a>
        <a href="/benchmarks">Benchmarks</a>
        <a href="/driver">Driver view</a>
        <a href="#architecture" class="active">Architecture overview</a>
        <a href="#qubo">QUBO formulation</a>
        <a href="#qaoa">QAOA + warm-start</a>
        <a href="#qae">QAE confidence engine</a>
        <a href="#zones">Zone decomposition</a>
        <a href="#api">API reference</a>
      </aside>
      <main class="content">
        <h1>ADAS system overview</h1>
        <div class="box">
          <p>ADAS is a connected decision layer for emergency response. It picks the ambulance, checks hospital capacity, coordinates the route, and estimates whether the plan will hold under uncertainty.</p>
        </div>
        <h2 id="architecture">Architecture overview</h2>
        <p>The system combines a fast simulation layer, classical baselines, a quantum search routine, and a confidence estimator. This gives the product an honest evaluation story rather than a single “black-box” optimizer.</p>
        <h2 id="qubo">QUBO formulation</h2>
        <p>Dispatch and lane coordination are encoded as a binary optimization problem with assignment costs based on travel time, capacity, and route risk.</p>
        <h2 id="qaoa">QAOA + warm-start</h2>
        <p>QAOA is used to explore the structured assignment space, while a classical warm start provides a physically plausible baseline for faster convergence.</p>
        <h2 id="qae">QAE confidence engine</h2>
        <p>Quantum amplitude estimation is used to estimate the probability that the selected response plan meets the critical time window, while classical Monte Carlo remains the fallback benchmark.</p>
        <h2 id="zones">Zone decomposition</h2>
        <p>Large city layouts are partitioned into zones so re-optimization stays tractable. Boundary conditions then reconcile assignments across adjacent zones.</p>
        <h2 id="api">API reference</h2>
        <p>Use the FastAPI routes under <code>/incidents</code>, <code>/assignments</code>, <code>/hospitals</code>, and <code>/benchmarks</code> to drive simulation state, assign ambulance responses, and inspect benchmark output.</p>
      </main>
    </div>
  </body>
</html>
"""


app = FastAPI(title="ADAS API", docs_url=None, redoc_url=None, openapi_url=None)

# Keep deployed Firebase origins available even when the Render environment
# variable is unset or only contains local development origins.
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = {
	"https://adas-nav.web.app",
	"https://adas-nav.firebaseapp.com",
	"http://localhost:5173",
	"http://127.0.0.1:5173",
}
allowed_origins.update(origin.strip() for origin in allowed_origins_str.split(",") if origin.strip())

app.add_middleware(
	CORSMiddleware,
	allow_origins=sorted(allowed_origins),
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(incidents.router, prefix="/incidents", tags=["incidents"])
app.include_router(assignments.router, prefix="/assignments", tags=["assignments"])
app.include_router(benchmarks.router, prefix="/benchmarks", tags=["benchmarks"])
app.include_router(hospitals.router, prefix="/hospitals", tags=["hospitals"])
app.include_router(map_data.router, prefix="/map", tags=["map"])
app.include_router(operations.router, prefix="/operations", tags=["operations"])


def _frontend_redirect(path: str = "/") -> RedirectResponse:
	frontend_url = os.getenv("FRONTEND_URL", "https://adas-nav.web.app").rstrip("/")
	return RedirectResponse(url=f"{frontend_url}{path}", status_code=307)


@app.get("/", include_in_schema=False)
def landing_page() -> RedirectResponse:
	return _frontend_redirect()


@app.get("/laning", include_in_schema=False)
@app.get("/lane-plan", include_in_schema=False)
def lane_page() -> RedirectResponse:
	return _frontend_redirect("/laning")


@app.get("/dashboard", include_in_schema=False)
def dashboard_page() -> RedirectResponse:
	return _frontend_redirect("/dashboard")


@app.get("/driver", include_in_schema=False)
def driver_page() -> RedirectResponse:
	return _frontend_redirect("/driver")


@app.get("/benchmarks", include_in_schema=False)
def benchmarks_page() -> RedirectResponse:
	return _frontend_redirect("/benchmarks")


@app.get("/docs", include_in_schema=False)
def docs_page() -> RedirectResponse:
	return _frontend_redirect("/docs")


@app.get("/integrations", include_in_schema=False)
def integrations_page() -> RedirectResponse:
	return _frontend_redirect("/integrations")


@app.get("/health")
def health() -> dict[str, str]:
	return {"status": "ok"}


@app.post("/demo/reset")
def reset_demo() -> dict[str, str]:
	init_simulation()
	benchmarks.clear_benchmark_cache()
	from adas.app_state import clear_request_log
	clear_request_log()
	return {"status": "reset"}
