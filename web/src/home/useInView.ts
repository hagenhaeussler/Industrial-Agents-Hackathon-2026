import { useEffect, useRef, useState } from "react";

/** True once the element has come near the viewport. It stays true, so loaded content is kept. */
export function useInView<T extends Element>(margin = "300px") {
  const ref = useRef<T>(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const element = ref.current;
    if (!element || seen) return;
    const observer = new IntersectionObserver(
      (entries) => entries.some((entry) => entry.isIntersecting) && setSeen(true),
      { rootMargin: margin },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [margin, seen]);
  return [ref, seen] as const;
}
