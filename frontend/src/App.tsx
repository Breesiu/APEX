import React from 'react';
import PosterEditPanel from './components/PosterEditPanel';

function App() {
  return (
    <div className="container modern-layout">
      {/* 顶部标题区 */}
      <div className="header app-header">
        <h1 className="app-title" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px' }}>
             APEX: Academic Poster Editing Agentic Expert
        </h1>
        {/* Subtitle removed via CSS styling */}
      </div>

      {/* 主面板区 */}
      <PosterEditPanel />
    </div>
  );
}

export default App;
