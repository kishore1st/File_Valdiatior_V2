import { OktaAuth } from "@okta/okta-auth-js";
import { createContext, useContext, useEffect, useState } from "react";

const okta = new OktaAuth({
  issuer: import.meta.env.VITE_OKTA_ISSUER,
  clientId: import.meta.env.VITE_OKTA_CLIENT_ID,
  redirectUri: window.location.origin + "/login/callback",
  scopes: ["openid", "profile", "email"],
});

const Ctx = createContext<{ login(): void; logout(): void; okta: OktaAuth } | null>(null);

export function OktaProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    (async () => {
      if (await okta.isLoginRedirect()) {
        const { tokens } = await okta.token.parseFromUrl();
        if (tokens?.accessToken) sessionStorage.setItem("okta_token", tokens.accessToken.accessToken);
        await okta.tokenManager.setTokens(tokens || {});
        window.history.replaceState({}, "", "/");
      }
    })();
  }, []);
  return (
    <Ctx.Provider value={{
      login: () => okta.signInWithRedirect(),
      logout: () => { sessionStorage.removeItem("okta_token"); okta.signOut(); },
      okta,
    }}>{children}</Ctx.Provider>
  );
}

export const useOkta = () => { const v = useContext(Ctx); if (!v) throw new Error("no okta"); return v; };