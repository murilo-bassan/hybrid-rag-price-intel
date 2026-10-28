"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLang } from "@/lib/i18n";

export default function Nav() {
  const path = usePathname();
  const { lang, setLang, t } = useLang();
  return (
    <nav className="nav">
      <Link href="/" className="brand">
        <span className="mark"><i /><i /><i /><i /></span>
        <span>
          <span className="label">{t("hybrid rag · price intelligence")}</span>
          <br />
          <b>priceintel</b>
        </span>
      </Link>
      <div className="links">
        <Link href="/" data-active={path === "/"}>{t("research")}</Link>
        <Link href="/eval" data-active={path === "/eval"}>{t("evaluation")}</Link>
        <a href="http://localhost:8900/docs" target="_blank" rel="noreferrer">api ↗</a>
        <span className="seg" style={{ marginLeft: 8 }}>
          {(["en", "pt"] as const).map((l) => (
            <button key={l} data-on={lang === l} onClick={() => setLang(l)}>{l.toUpperCase()}</button>
          ))}
        </span>
      </div>
    </nav>
  );
}
