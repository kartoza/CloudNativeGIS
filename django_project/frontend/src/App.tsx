import * as Sentry from "@sentry/react";
import React from 'react';
import { createRoot } from "react-dom/client";
import './styles/index.scss';
import reportWebVitals from './reportWebVitals';
import Home from "./Home";
import ErrorBoundary from "./components/ErrorBoundary";


Sentry.init({
    dsn: 'SENTRY_DSN',
    tunnel: '/sentry-proxy/',
    tracesSampleRate: 0.5
})

const rootElement = document.getElementById('app')!
const root = createRoot(rootElement);
root.render(
    <ErrorBoundary>
        <Home/>
    </ErrorBoundary>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
