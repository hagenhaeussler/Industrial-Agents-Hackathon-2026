import { Search, X } from 'lucide-react';
import { useDeferredValue, useMemo } from 'react';
import type { Asset } from '../api/types';
import { floorName, isPart, spaceName } from '../map/model';
import type { Model } from '../map/model';

type Props = {
  model: Model;
  query: string;
  onQuery: (query: string) => void;
  selected: ReadonlySet<string>;
  onToggle: (assetId: string) => void;
  focusId: string | null;
  onFocus: (assetId: string) => void;
};

const words = (text: string) => text.toLowerCase().split(/\s+/).filter(Boolean);
const haystack = (asset: Asset, model: Model) => `${asset.name} ${asset.type.replace(/_/g, ' ')} ${spaceName(model, asset.space_id)}`.toLowerCase();

/** Parts grouped by floor, then room. Furniture appears only when searched for. */
export function PartsList({ model, query, onQuery, selected, onToggle, focusId, onFocus }: Props) {
  const deferred = useDeferredValue(query);
  const groups = useMemo(() => {
    const terms = words(deferred);
    const hits = model.snapshot.building.assets.filter(asset => (terms.length ? terms.every(term => haystack(asset, model).includes(term)) : isPart(asset)) || selected.has(asset.id));
    return model.floors.map(floor => {
      const rooms = new Map<string, Asset[]>();
      for (const asset of hits) if (asset.floor_id === floor.id) rooms.set(asset.space_id, [...(rooms.get(asset.space_id) ?? []), asset]);
      return { floor, rooms: [...rooms.entries()].sort((a, b) => spaceName(model, a[0]).localeCompare(spaceName(model, b[0]), 'en', { numeric: true })) };
    }).filter(group => group.rooms.length);
  }, [model, deferred, selected]);
  const count = groups.reduce((sum, group) => sum + group.rooms.reduce((n, [, assets]) => n + assets.length, 0), 0);

  return <section className="parts" aria-labelledby="parts-title">
    <div className="parts-head">
      <h2 id="parts-title">Parts in this building</h2>
      <span className="muted">{count} shown</span>
    </div>
    <div className="search-field">
      <Search size={17} aria-hidden="true"/>
      <label className="sr-only" htmlFor="part-search">Search parts</label>
      <input id="part-search" type="search" value={query} onChange={event => onQuery(event.target.value)} placeholder="Search parts, types or rooms" autoComplete="off"/>
      {query && <button className="clear" onClick={() => onQuery('')} aria-label="Clear search"><X size={16}/></button>}
    </div>
    <div className="parts-scroll">
      {!count && <p className="empty">Nothing matches “{query}”. Try a type such as “printer” or a room name.</p>}
      {groups.map(({ floor, rooms }) => <div key={floor.id} className="parts-floor">
        <h3 className="floor-heading">{floor.name}</h3>
        {rooms.map(([spaceId, assets]) => <div key={spaceId} className="parts-room">
          <h4>{spaceName(model, spaceId)}</h4>
          <ul>
            {assets.map(asset => <li key={asset.id} className={`part-row ${selected.has(asset.id) ? 'selected' : ''} ${focusId === asset.id ? 'focused' : ''}`}>
              <input type="checkbox" id={`pick-${asset.id}`} checked={selected.has(asset.id)} onChange={() => { onToggle(asset.id); onFocus(asset.id); }}/>
              <label htmlFor={`pick-${asset.id}`} className="sr-only">Add {asset.name} to the tour</label>
              <button className="part-name" onClick={() => onFocus(asset.id)} aria-label={`Show ${asset.name} on the map, ${spaceName(model, spaceId)}, ${floorName(model, floor.id)}`}>
                <strong>{asset.name}</strong><span>{asset.type.replace(/_/g, ' ')}</span>
              </button>
            </li>)}
          </ul>
        </div>)}
      </div>)}
    </div>
  </section>;
}
