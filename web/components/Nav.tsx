"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Nav() {
  const path = usePathname();
  return (
    <nav className="nav">
      <Link href="/" className="brand">
        <span className="mark"><i /><i /><i /><i /></span>
        <span>
          <span className="label">hybrid rag · price intelligence</span>
          <br />
          <b>priceintel</b>
        </span>
      </Link>
      <div className="links">
        <Link href="/" data-active={path === "/"}>research</Link>
        <Link href="/eval" data-active={path === "/eval"}>evaluation</Link>
        <a href="http://localhost:8900/docs" target="_blank" rel="noreferrer">api ↗</a>
      </div>
    </nav>
  );
}
