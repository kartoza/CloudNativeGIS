import React from 'react';
import './styles/App.scss';

function Home() {

  const buttonClicked = () => {
    throw new Error('error!')
  }

  return (
    <div className="App">
      <header className="App-header">
        <p>
          Edit <code>src/App.tsx</code> and save to
        </p>
        <div
          className="App-link"
          onClick={buttonClicked}
        >
          Error Test
        </div>
      </header>
    </div>
  );
}

export default Home;
