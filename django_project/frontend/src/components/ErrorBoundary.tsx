import React, {ErrorInfo, ReactNode} from "react";
import * as Sentry from "@sentry/react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo
}

export default class ErrorBoundary extends React.Component<Props, State> {
    constructor(props: any) {
        super(props);
        this.state = {
            hasError: false,
            errorInfo: null,
            error: null
        };
    }

    static getDerivedStateFromError(_: Error) : State {
        // Update state so the next render will show the fallback UI.
        return {hasError: true, error: _, errorInfo: null};
    }

    componentDidCatch(error: Error, errorInfo: any) {
        // You can also log the error to an error reporting service
        this.setState({
            error: error,
            errorInfo: errorInfo
        })

        // Send to sentry
        Sentry.captureException(error);
    }

    render() {
        if (this.state.hasError) {
            // You can render any custom fallback UI
            return <div>
                <h1>Something went wrong!</h1>
                <p>
                    { this.state.error ? this.state.error.message : null }
                </p>
            </div>;
        }

        return this.props.children;
    }
}
