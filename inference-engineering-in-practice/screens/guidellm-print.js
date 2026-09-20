// Print patches for GuideLLM 0.7.4's HTML report, for screenshot S10.
//
// Three things the report does not have to care about on a screen and
// the book does on paper:
//
//   1. Its chart type is 10 CSS px in a 631 px card, which prints at
//      about 5 pt on a 4.4-inch page. screens/shots.json raises it to
//      14 px; this then slides the rotated y-axis title clear of the
//      wider tick labels, keeping the unit on the axis.
//   2. Its five series (p50, p90, p95, p99, mean) are told apart by
//      colour alone, and the paperback is black on white. Each gets a
//      line style, keyed by its own stroke colour so the legend swatch
//      picks up the same one. No colour is changed.
//   3. The two cards the book captures get a stable attribute, so the
//      capture can address them without a brittle CSS path.
//
// Nothing here touches a number, an axis range or a data point.
() => {
  const pick = (re, tag) => {
    const el = Array.from(document.querySelectorAll('div')).find(
      (e) => re.test((e.textContent || '').trim()));
    if (el) el.setAttribute('data-shot', tag);
    return Boolean(el);
  };
  const found = [pick(/^Time to First Token vs RPS/, 'ttft'),
                 pick(/^Throughput vs RPS/, 'thru')];

  let moved = 0;
  document.querySelectorAll('svg text[transform*="rotate(-90)"]').forEach((t) => {
    const m = (t.getAttribute('transform') || '')
      .match(/translate\(\s*(-?[\d.]+)[,\s]+(-?[\d.]+)\s*\)/);
    if (!m) return;
    t.setAttribute('transform',
      'translate(' + (Number(m[1]) - 22) + ', ' + m[2] + ') rotate(-90)');
    moved++;
  });

  const DASH = {
    '#E1E2E9': '2 7',        // p50
    '#03C883': '16 8',       // p90
    '#FFC93F': '5 6',        // p95
    '#FF8228': '22 7 4 7',   // p99
    '#2A8EFD': '',           // mean, the only solid line
  };
  let styled = 0;
  document.querySelectorAll('[stroke]').forEach((e) => {
    const d = DASH[(e.getAttribute('stroke') || '').toUpperCase()];
    if (d === undefined) return;
    e.style.strokeDasharray = d || 'none';
    styled++;
  });

  return { cards: found, axisTitlesMoved: moved, seriesStyled: styled };
}
