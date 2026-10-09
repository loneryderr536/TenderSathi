import { useState } from "react";

/** tabs: [{ label, content }] */
export default function Tabs({ tabs }) {
  const [active, setActive] = useState(0);
  return (
    <div className="rounded-xl border border-stone-200 bg-white shadow-sm">
      <div role="tablist" className="flex overflow-x-auto border-b border-stone-200">
        {tabs.map((tab, i) => (
          <button
            key={tab.label}
            role="tab"
            aria-selected={i === active}
            onClick={() => setActive(i)}
            className={`shrink-0 px-4 py-3 text-sm font-medium ${
              i === active ? "border-b-2 border-brand-600 text-brand-700" : "text-stone-600 hover:text-stone-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" className="p-4 sm:p-6">{tabs[active].content}</div>
    </div>
  );
}
