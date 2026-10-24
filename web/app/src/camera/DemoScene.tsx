/** An architectural illustration, never presented as a live camera image. */
export function DemoScene() {
  return <svg className="demo-scene" viewBox="0 0 1000 1400" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs>
      <linearGradient id="floor" x2="0.4" y2="1"><stop stopColor="#c0beb5"/><stop offset="1" stopColor="#e1dfd6"/></linearGradient>
      <linearGradient id="left" x2="1" y2="0"><stop stopColor="#d4d4ca"/><stop offset="1" stopColor="#eeeae0"/></linearGradient>
      <linearGradient id="right" x2="0" y2="1"><stop stopColor="#d8d7cf"/><stop offset="1" stopColor="#b8b8ad"/></linearGradient>
      <linearGradient id="glass" x2="1" y2="1"><stop stopColor="#61726b"/><stop offset="0.5" stopColor="#9ba59b"/><stop offset="1" stopColor="#b4baab"/></linearGradient>
    </defs>
    <path fill="#e9e7df" d="M0 0h1000v1400H0z"/>
    <path fill="url(#floor)" d="m0 1400 410-770h180l410 770z"/>
    <path fill="url(#left)" d="M0 0 410 490v140L0 1400z"/>
    <path fill="url(#right)" d="m1000 0-410 490v140l410 770z"/>
    <path fill="#dad9d0" d="M410 490h180v140H410z"/>
    <path fill="#88958b" d="M450 523h102v107H450z"/>
    <path fill="#d6dcd2" d="M456 530h90v90h-90z"/>
    <path fill="#a9b3a3" d="M470 562h12v58h-12zm20-20h25v78h-25zm30 36h12v42h-12z"/>
    <path fill="#f8f7ee" d="m154 0 319 490h54L846 0z"/>
    <g fill="#fffff6"><path d="M385 25h230l-28 46H413z"/><path d="M427 169h146l-18 32H445z"/><path d="M456 288h88l-12 23h-64z"/><path d="M477 394h46l-6 15h-34z"/></g>
    <g stroke="#b1b2a7" strokeWidth="2" opacity=".65"><path d="M0 50 410 503M0 211l410 316M0 547l410 28M1000 50 590 503M1000 211 590 527M0 1038l410-431M1000 1038 590 607"/><path d="m73 1400 370-770m484 770L557 630M0 983h1000M0 1202h1000M315 809h370M375 697h250"/></g>
    <path fill="#8d948a" d="M0 222 218 394v391L0 1070z"/>
    <path fill="url(#glass)" d="M0 242 202 402v372L0 1030z"/>
    <path fill="#d6d9cf" d="m68 300 9 7v622l-9 12z"/>
    <path fill="#444e47" d="m164 565 8 1v70l-8 3z"/>
    <path fill="#9a9d91" d="m270 435 78 61v184l-78 101z"/>
    <path fill="#d0d3c7" d="m278 451 62 49v174l-62 80z"/>
    <path fill="#8f968b" d="m650 488 87-68v365l-87-100z"/>
    <path fill="#78877b" d="m658 495 71-56v326l-71-84z"/>
    <path fill="#f4f3e8" d="m766 290 234-186v961l-234-286z"/>
    <path fill="#b4b9aa" d="m782 337 218-171v837l-218-261z"/>
    <path fill="url(#glass)" d="m793 349 207-162v787L793 728z"/>
    <g stroke="#d2d7c8" strokeWidth="6"><path d="M847 307v486m79-548v646m-131-358 205-18"/></g>
    <path fill="#6a7a65" d="m860 808 98 97-12 135-69-88z"/>
    <g fill="#667b59"><ellipse cx="907" cy="733" rx="41" ry="96" transform="rotate(-22 907 733)"/><ellipse cx="882" cy="739" rx="28" ry="73" transform="rotate(-49 882 739)"/><ellipse cx="924" cy="764" rx="31" ry="85" transform="rotate(25 924 764)"/></g>
    <g fill="#555c51" fontFamily="sans-serif" fontSize="13"><text x="294" y="480" transform="rotate(34 294 480)">0.03</text><text x="675" y="479" transform="rotate(-34 675 479)">0.14</text></g>
  </svg>;
}
