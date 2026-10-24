import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource-variable/manrope';
import 'blobatar/motion.css';
import './styles.css';
import './app.css';
import App from './App';

const root = document.getElementById('root');
if (!root) throw new Error('The app root is missing.');
createRoot(root).render(<StrictMode><App/></StrictMode>);
