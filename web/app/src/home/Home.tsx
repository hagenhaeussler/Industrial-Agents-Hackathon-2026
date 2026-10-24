import { ArrowLeft, ArrowRight, Building2, Check, ChevronRight, LoaderCircle, Plus, Search } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { api, mockMode } from '../api/client';
import type { BuildingSummary, TeamSummary } from '../api/types';
import { linkHandler, navigate, useLocation, withSticky } from '../router';
import { DemoBadge } from '../ui/DemoBadge';
import { VoiceOrb } from '../voice/VoiceOrb';
import { NewBuilding } from './NewBuilding';
import './Home.css';

/** Quiet entry → shared team catalog → existing building desk. */
export function Home() {
  const { query } = useLocation();
  const teamId = query.get('team');
  const entered = query.get('view') === 'teams' || !!teamId;
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [teamError, setTeamError] = useState<string | null>(null);
  const [loadingTeams, setLoadingTeams] = useState(false);
  const [retry, setRetry] = useState(0);
  const [buildings, setBuildings] = useState<BuildingSummary[]>([]);
  const [buildingError, setBuildingError] = useState<string | null>(null);
  const [loadingBuildings, setLoadingBuildings] = useState(false);
  const [search, setSearch] = useState('');
  const [creating, setCreating] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [createdId, setCreatedId] = useState<string | null>(null);
  const panelTitle = useRef<HTMLHeadingElement>(null);
  const team = teams.find(item => item.id === teamId);

  useEffect(() => {
    if (!entered) return;
    let active = true;
    setLoadingTeams(true); setTeamError(null);
    api.teams().then(value => { if (active) setTeams(value); }, error => { if (active) setTeamError(error instanceof Error ? error.message : 'Teams could not load.'); })
      .finally(() => { if (active) setLoadingTeams(false); });
    return () => { active = false; };
  }, [entered, retry, refresh]);

  useEffect(() => {
    setSearch(''); setCreating(false); setCreatedId(null); setBuildings([]); setBuildingError(null);
  }, [teamId]);

  useEffect(() => {
    if (!teamId) return;
    let active = true;
    setLoadingBuildings(true); setBuildingError(null);
    api.teamBuildings(teamId).then(value => { if (active) setBuildings(value); }, error => { if (active) setBuildingError(error instanceof Error ? error.message : 'Buildings could not load.'); })
      .finally(() => { if (active) setLoadingBuildings(false); });
    return () => { active = false; };
  }, [teamId, refresh]);

  useEffect(() => { if (teamId) panelTitle.current?.focus({ preventScroll: true }); }, [teamId]);

  if (!entered) return <main className="home-entry">
    <div className="home-identity">
      <div className="home-launch"><VoiceOrb phase="idle" label="Choose your team" onClick={() => navigate('/?view=teams')}/></div>
      <h1>Talk to Your Building</h1>
    </div>
  </main>;

  const shown = buildings.filter(item => `${item.name} ${item.id}`.toLowerCase().includes(search.trim().toLowerCase()));
  return <main className={`workspace-entry${teamId ? ' has-team' : ''}`}>
    <section className="team-picker" aria-labelledby="team-title">
      <header className="workspace-heading">
        <button type="button" className="workspace-back" aria-label="Back to home" onClick={() => navigate('/')}><ArrowLeft size={19}/></button>
        <h1 id="team-title">Choose your team</h1>
      </header>
      {mockMode && <DemoBadge reason="Example team catalog"/>}
      {loadingTeams && !teams.length && <p className="workspace-loading" role="status"><LoaderCircle className="spin" size={17}/>Loading teams…</p>}
      {teamError && <div className="workspace-error" role="alert"><p>{teamError}</p><button className="link-button" onClick={() => setRetry(value => value + 1)}>Try again</button></div>}
      <div className="team-options">
        {teams.map(item => <button type="button" key={item.id} className={`team-option${item.id === teamId ? ' selected' : ''}`} aria-pressed={item.id === teamId}
          onClick={() => navigate(`/?team=${encodeURIComponent(item.id)}`)}>
          <span><strong>{item.name}</strong><small>{item.building_count} {item.building_count === 1 ? 'building' : 'buildings'}</small></span>
          {item.id === teamId ? <Check size={18} aria-hidden="true"/> : <ChevronRight size={18} aria-hidden="true"/>}
        </button>)}
      </div>
    </section>

    {teamId && <section key={teamId} className="team-buildings-panel" aria-label="Team buildings">
      <header className="buildings-heading">
        <div><p>{team?.name ?? 'Your team'}</p><h2 ref={panelTitle} tabIndex={-1}>{creating ? 'Create a building' : 'Choose a building'}</h2></div>
        <button className="workspace-back" aria-label="Close building panel" onClick={() => navigate('/?view=teams')}><ArrowLeft size={19}/></button>
      </header>
      {creating ? <NewBuilding key={teamId} teamId={teamId} onBack={() => setCreating(false)} onCreated={id => { setCreatedId(id); setRefresh(value => value + 1); }}/>
        : <>
          <div className="building-search"><Search size={17} aria-hidden="true"/><label className="sr-only" htmlFor="team-building-search">Search buildings</label><input id="team-building-search" type="search" placeholder="Search buildings" value={search} onChange={event => setSearch(event.target.value)}/></div>
          <div className="team-buildings-scroll">
            {buildingError && <div className="workspace-error" role="alert"><p>{buildingError}</p><button className="link-button" onClick={() => setRefresh(value => value + 1)}>Try again</button></div>}
            {loadingBuildings && <p className="workspace-loading" role="status"><LoaderCircle className="spin" size={17}/>Loading buildings…</p>}
            {!loadingBuildings && !buildingError && !shown.length && <p className="workspace-empty">{search.trim() ? 'No buildings match your search.' : 'Your first building starts here.'}</p>}
            <ul className="team-building-list">{shown.map(item => {
              const url = `/desk?building=${encodeURIComponent(item.id)}&team=${encodeURIComponent(teamId)}`;
              return <li key={item.id}><a href={withSticky(url)} onClick={linkHandler(url)} className={createdId === item.id ? 'just-created' : ''}>
                <span className="building-symbol"><Building2 size={19} aria-hidden="true"/></span><span><strong>{item.name}</strong><small>{item.floors} {item.floors === 1 ? 'floor' : 'floors'}{createdId === item.id ? ' · Just added' : ''}</small></span><ArrowRight size={17} aria-hidden="true"/>
              </a></li>;
            })}</ul>
          </div>
          <button type="button" className="workspace-create" disabled={!team} onClick={() => setCreating(true)}><Plus size={18}/>Create a new building</button>
          <a className="home-colab-link" href={withSticky('/colab')} onClick={linkHandler('/colab')}>Explore Munich Urban Colab <ArrowRight size={15}/></a>
        </>}
    </section>}
  </main>;
}
