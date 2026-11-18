import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { App } from "./App";
import { ProvedorAvisos } from "./components/ui";
import "./styles.css";

const cliente = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: true, staleTime: 5_000 } },
});

createRoot(document.getElementById("raiz")!).render(
  <StrictMode>
    <QueryClientProvider client={cliente}>
      <ProvedorAvisos>
        <BrowserRouter basename="/painel">
          <App />
        </BrowserRouter>
      </ProvedorAvisos>
    </QueryClientProvider>
  </StrictMode>,
);
