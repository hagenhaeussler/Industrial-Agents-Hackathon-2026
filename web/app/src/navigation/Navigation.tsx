import { ArrowLeft, ArrowRight, ArrowUp, Check, ChevronDown, Flag, MoveUpRight } from 'lucide-react';
import type { Destination, RouteStep, Turn } from './routes';

export function TurnIcon({ turn, size = 36 }: { turn: Turn; size?: number }) {
  if (turn === 'left') return <ArrowLeft size={size} strokeWidth={2.5}/>;
  if (turn === 'right') return <ArrowRight size={size} strokeWidth={2.5}/>;
  if (turn === 'arrived') return <Check size={size} strokeWidth={2.5}/>;
  return <ArrowUp size={size} strokeWidth={2.5}/>;
}

export function RouteBanner({ destination, step, onOpen }: { destination: Destination; step: RouteStep; onOpen: () => void }) {
  return <button className="route-banner surface" onClick={onOpen} aria-label="Open route">
    <span className="turn-icon"><TurnIcon turn={step.turn}/></span>
    <span className="route-copy"><span className="route-instruction">{step.instruction}</span><span className="route-destination">{destination.name} <span>· {destination.room}</span></span></span>
    <span className="route-distance">{step.meters}<span>metres</span></span>
    <ChevronDown size={18} className="route-chevron"/>
  </button>;
}

export function FloorMap({ step, destination, onOpen }: { step: RouteStep; destination: Destination; onOpen: () => void }) {
  const endpoint = destination.steps[destination.steps.length - 1]?.position ?? step.position;
  const points = destination.steps.map(item => item.position.join(',')).join(' ');
  return <button className="floor-map surface" onClick={onOpen} aria-label="Enlarge map and change destination">
    <span className="map-heading"><strong>Ground floor</strong><MoveUpRight size={14}/></span>
    <svg viewBox="10 11 170 123" aria-label={`Map to the ${destination.name}`} role="img">
      <path d="M12 13h166v119H12z" fill="#f1f0ea" stroke="#c9cbc1" strokeWidth="1.3"/>
      <path d="M67 24h22v23h75v21H89v55H67V68H24V47h43z" fill="#fff"/>
      <g fill="none" stroke="#b9bdb0" strokeWidth="1.3"><path d="M12 47h55V13m22 0v34h89M12 68h55v64m22 0V68h89M50 13v34m70-34v34m35-34v34M12 94h55m22 0h89m31-26v64"/></g>
      <polyline points={points} fill="none" stroke="#d4f64d" strokeWidth="11" strokeLinejoin="round" strokeLinecap="round"/>
      <polyline points={points} fill="none" stroke="#4a5c1f" strokeWidth="2.3" strokeLinejoin="round" strokeLinecap="round" strokeDasharray="2 5"/>
      <circle cx={endpoint[0]} cy={endpoint[1]} r="5" fill="#20251a"/>
      <circle cx={step.position[0]} cy={step.position[1]} r="8" fill="#fff"/>
      <circle cx={step.position[0]} cy={step.position[1]} r="5" fill="#20251a"/>
      <path d={`m${step.position[0] - 4} ${step.position[1] - 12} 4-6 4 6`} fill="#20251a"/>
      <text x="145" y="119" fill="#717569" fontSize="9" fontFamily="inherit">N ↑</text>
    </svg>
  </button>;
}

export function RouteOverlay({ step }: { step: RouteStep }) {
  if (step.turn === 'arrived') return <div className="arrival-marker" aria-hidden="true"><Flag size={34}/></div>;
  const path = step.turn === 'left' ? 'M210 690 210 390 100 390' : step.turn === 'right' ? 'M210 690 210 390 320 390' : 'M210 690 210 300';
  return <svg className="route-overlay" viewBox="0 0 420 820" preserveAspectRatio="none" aria-hidden="true">
    <defs><linearGradient id="routeFade" gradientUnits="userSpaceOnUse" x1="210" y1="700" x2="210" y2="300"><stop stopColor="#dcff58" stopOpacity=".15"/><stop offset=".65" stopColor="#dcff58" stopOpacity=".65"/><stop offset="1" stopColor="#dcff58" stopOpacity=".95"/></linearGradient></defs>
    <path d={path} stroke="#26301d" strokeWidth="32" fill="none" strokeLinejoin="round" opacity=".12"/>
    <path d={path} stroke="url(#routeFade)" strokeWidth="25" fill="none" strokeLinejoin="round"/>
    {step.turn === 'straight' ? <path d="m183 332 27-32 27 32" fill="none" stroke="#e2ff77" strokeWidth="13" strokeLinecap="round" strokeLinejoin="round"/> : step.turn === 'left' ? <path d="m125 366-26 24 26 24" fill="none" stroke="#e2ff77" strokeWidth="13" strokeLinecap="round" strokeLinejoin="round"/> : <path d="m295 366 26 24-26 24" fill="none" stroke="#e2ff77" strokeWidth="13" strokeLinecap="round" strokeLinejoin="round"/>}
    <ellipse cx="210" cy="697" rx="18" ry="6" fill="#f1ffbd"/>
  </svg>;
}
