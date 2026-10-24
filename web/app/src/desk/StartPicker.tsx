import { Check, Search, X } from 'lucide-react';
import { useEffect, useId, useMemo, useRef, useState } from 'react';
import type { Model } from '../map/model';

type Props = { model: Model; open: boolean; current: string | null; onPick: (spaceId: string) => void; onClose: () => void; title?: string; hint?: string; clearLabel?: string; onClear?: () => void };

/** "Where are you now?" — a room picker, grouped by floor (UX J3b). */
export function StartPicker({ model, open, current, onPick, onClose, title = 'Where are you now?', hint = 'The tour starts here. You can also click a room on the map.', clearLabel, onClear }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const [query, setQuery] = useState('');
  const id = useId();
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) { setQuery(''); dialog.showModal(); }
    if (!open && dialog.open) dialog.close();
  }, [open]);
  const groups = useMemo(() => {
    const q = query.toLowerCase().trim();
    return [...model.floors].reverse().map(floor => ({
      floor,
      spaces: (model.spacesOn.get(floor.id) ?? []).filter(space => !q || `${space.name} ${space.ref} ${space.room_type.replace(/_/g, ' ')}`.toLowerCase().includes(q)).sort((a, b) => a.name.localeCompare(b.name, 'en', { numeric: true })),
    })).filter(group => group.spaces.length);
  }, [model, query]);

  return <dialog ref={ref} className="sheet picker-sheet" aria-labelledby={`${id}-title`} onClose={onClose} onCancel={onClose}>
    <header className="sheet-header">
      <div><h2 id={`${id}-title`}>{title}</h2><p>{hint}</p></div>
      <button className="icon-button" onClick={onClose} aria-label="Close"><X size={22}/></button>
    </header>
    <div className="search-field"><Search size={17} aria-hidden="true"/><label className="sr-only" htmlFor={`${id}-search`}>Search rooms</label><input id={`${id}-search`} type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Room name or number" autoComplete="off"/></div>
    {onClear && clearLabel && <button className="secondary-button picker-clear" onClick={onClear}>{clearLabel}</button>}
    <div className="picker-list">
      {groups.map(({ floor, spaces }) => <div key={floor.id}>
        <h3 className="floor-heading">{floor.name}</h3>
        {spaces.map(space => <button key={space.id} className={`destination-option ${space.id === current ? 'selected' : ''}`} onClick={() => onPick(space.id)}>
          <span><strong>{space.name}</strong><span>{space.room_type.replace(/_/g, ' ')}</span></span>{space.id === current && <Check size={18}/>}
        </button>)}
      </div>)}
    </div>
  </dialog>;
}
