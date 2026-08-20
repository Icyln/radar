"use client";

import { KeyboardEvent, useState } from "react";

export function TagInput({
  values,
  onChange,
  placeholder,
  maxItems,
  ariaLabel
}: {
  values: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  maxItems?: number;
  ariaLabel: string;
}) {
  const [value, setValue] = useState("");

  function add(raw: string) {
    const item = raw.trim();
    if (!item) return;
    if (maxItems && values.length >= maxItems) return;
    if (values.some((current) => current.toLocaleLowerCase() === item.toLocaleLowerCase())) {
      setValue("");
      return;
    }
    onChange([...values, item]);
    setValue("");
  }

  function keyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      add(value);
    }
    if (event.key === "Backspace" && !value && values.length) {
      onChange(values.slice(0, -1));
    }
  }

  return (
    <div className="rounded-xl border border-ui surface p-2 focus-within:border-[var(--accent)] focus-within:ring-2 focus-within:ring-emerald-700/10">
      <div className="flex flex-wrap gap-2">
        {values.map((item) => (
          <span key={item} className="inline-flex items-center gap-1.5 rounded-lg border border-ui surface-soft px-2.5 py-1.5 text-xs text-main">
            {item}
            <button type="button" className="text-faint hover:text-danger" aria-label={`Remove ${item}`} onClick={() => onChange(values.filter((value) => value !== item))}>×</button>
          </span>
        ))}
        <input
          aria-label={ariaLabel}
          className="min-w-[10rem] flex-1 border-0 bg-transparent px-1 py-1.5 text-sm text-main outline-none placeholder:text-[var(--text-faint)]"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={keyDown}
          onBlur={() => add(value)}
          placeholder={values.length === 0 ? placeholder : "Add another"}
          disabled={Boolean(maxItems && values.length >= maxItems)}
        />
      </div>
    </div>
  );
}
