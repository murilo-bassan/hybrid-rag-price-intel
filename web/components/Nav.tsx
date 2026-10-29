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
          <b>priceintel</b>
          <br />
          <span className="label">{t("Public price search")}</span>
        </span>
      </Link>
      <div className="links">
        <Link href="/" data-active={path === "/"}>{t("Search")}</Link>
        <Link href="/eval" data-active={path === "/eval"}>{t("Evaluation")}</Link>
        <a href="http://localhost:8900/docs" target="_blank" rel="noreferrer">API</a>
        <span className="seg" style={{ marginLeft: 8 }}>
          {(["en", "pt"] as const).map((l) => (
            <button key={l} data-on={lang === l} onClick={() => setLang(l)}>{l.toUpperCase()}</button>
          ))}
        </span>
      </div>
    </nav>
  );
}
