import { findDestination } from '../navigation/routes';

export function getDemoReply(message: string): string {
  const destination = findDestination(message);
  if (destination) return `Ich zeige dir den Demo-Weg zur ${destination.name}, ${destination.room}. ${destination.description} Die Route kannst du Schritt für Schritt ausprobieren.`;
  if (/treppe|barriere|aufzug|rollstuhl/i.test(message)) return 'Alle Demo-Ziele liegen im Erdgeschoss. Die Beispielrouten haben keine Treppen. Echte Zugangs- und Gebäudedaten sind noch nicht verbunden.';
  if (/kamera|position|standort|wo bin/i.test(message)) return 'Das Kamerabild kommt direkt von deinem Gerät. Deine Position wird noch nicht erkannt. Die Minimap zeigt eine Demo-Position, die du über die Routenschritte bewegst.';
  if (/dokument|plan|gebäude|floor|etage/i.test(message)) return 'Der Demo-Grundriss enthält die Werkstatt (0.14), Besprechung (0.08) und Kaffeeküche (0.03) im Erdgeschoss. Eigene Gebäudedokumente sind noch nicht verbunden.';
  return 'Ich bin hier als Demo-Guide. Frage mich nach der Werkstatt, Besprechung oder Kaffeeküche. Ich kann die Beispielroute für dich wechseln. Ein Sprachmodell ist noch nicht verbunden.';
}
