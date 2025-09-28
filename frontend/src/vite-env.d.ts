/// <reference types="vite/client" />

declare global {
  interface ImportMeta {
    env: {
      VITE_API_BASE_URL?: string;
      REACT_APP_BACKEND_URL?: string;
      REACT_APP_VAPI_PUBLIC_KEY?: string;
      REACT_APP_VAPI_ASSISTANT_ID?: string;
      [key: string]: string | undefined;
    };
  }

  const process: {
    env: {
      REACT_APP_BACKEND_URL?: string;
      REACT_APP_VAPI_PUBLIC_KEY?: string;
      REACT_APP_VAPI_ASSISTANT_ID?: string;
      [key: string]: string | undefined;
    };
  };
}

export {};
