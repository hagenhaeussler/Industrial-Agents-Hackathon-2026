import { ArrowRight, LoaderCircle, Search } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { api, mockMode } from '../api/client';
import type { BuildingSummary } from '../api/types';
import { linkHandler, withSticky } from '../router';
import { DemoBadge } from '../ui/DemoBadge';
import { scenario } from '../demo/scenario';

/** `/`: the building picker, with the demo scenario first (UX J1). */
export function Home() {
  const [buildings, setBuildings] = useState<BuildingSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  useEffect(() => { api.buildings().then(setBuildings, (reason: unknown) => setError(reason instanceof Error ? reason.message : 'The building list did not load.')); }, []);
  const shown = useMemo(() => {
    const q = query.toLowerCase().trim();
    return (buildings ?? []).filter(item => !q || `${item.name} ${item.id} ${item.source}`.toLowerCase().includes(q)).slice(0, 60);
  }, [buildings, query]);
  const demoName = buildings?.find(item => item.id === scenario.building_id)?.name;

  return <main className="home">
    <section className="home-hero">
      <p className="product">Talk to Your Building {mockMode && <DemoBadge reason="Mock mode: bundled kit data"/>}</p>
      <h1>Say what you need, not where it is.</h1>
      <p className="lede">Find parts, plan the shortest collection tour and take it with you on your phone.</p>
      <a className="primary-button hero-cta" href={withSticky('/desk?demo=hero')} onClick={linkHandler('/desk?demo=hero')}>Open the demo{demoName ? `: ${demoName}` : ''}<ArrowRight size={18}/></a>
    </section>
    <section className="home-list surface" aria-labelledby="buildings-title">
      <div className="parts-head"><h2 id="buildings-title">Buildings</h2>{buildings && <span className="muted">{buildings.length}</span>}</div>
      <div className="search-field"><Search size={17} aria-hidden="true"/><label className="sr-only" htmlFor="building-search">Search buildings</label><input id="building-search" type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Name or id" autoComplete="off"/></div>
      {error && <p className="plan-error" role="alert">{error}</p>}
      {!buildings && !error && <p className="loading"><LoaderCircle className="spin" size={18}/>Loading buildings…</p>}
      <ul className="building-list">
        {shown.map(item => <li key={item.id}><a href={withSticky(`/desk?building=${encodeURIComponent(item.id)}`)} onClick={linkHandler(`/desk?building=${encodeURIComponent(item.id)}`)}>
          <strong>{item.name}</strong><span>{item.floors} {item.floors === 1 ? 'floor' : 'floors'}{item.has_lift ? ', lift' : ''}{item.has_stairs ? ', stairs' : ''} · {item.id}</span><ArrowRight size={16}/>
        </a></li>)}
      </ul>
    </section>
  </main>;
}
