/* STORMWATCH release notes: available locally; no external network required. */
(() => {
  'use strict';
  const STORAGE_KEY = 'stormwatch.releaseNotes.dismissedVersion';
  const RELEASES = [
    {version:'0.10.4', date:'2026-10-15', title:'AI briefing recovery and tester thank-you', subtitle:'A sourced AI search fallback when RSS feeds fail, plus a personal note to everyone testing the site.', changes:[{icon:'◎',title:'Briefing fallback',description:'When news RSS feeds are unavailable, OpenAI can search for verified coverage and provide source links. Uncited results are not published.'},{icon:'◷',title:'More useful errors',description:'API authentication, quota, model access and timeouts now show distinct troubleshooting messages.'},{icon:'↗',title:'Feedback invitation',description:'The release dialog includes a message from the creator and a direct Send Feedback action.'}]},
    {version:'0.10.3', date:'2026-10-15', title:'Simpler workspace and briefing reliability', subtitle:'More room for storm monitoring, and a fix for the RSS feed parser.', changes:[{icon:'▤',title:'Focused navigation',description:'Live, Archive and Send Feedback stay visible. Briefing, About, Support, release notes, and source diagnostics now live under Menu.'},{icon:'◷',title:'Reliable feed parsing',description:'RSS and Atom feeds use the standard Python XML parser, avoiding an optional dependency absent from Vercel.'},{icon:'◎',title:'Source diagnostics',description:'Briefing now shows per-source availability when a news provider is unreachable.'}]},
    {version:'0.10.2', date:'2026-10-15', title:'Feedback for everyone', subtitle:'Anyone with the link can test STORMWATCH and send feedback directly.', changes:[{icon:'↗',title:'Send feedback',description:'Visible feedback button on desktop and mobile, with no signup or approval needed.'},{icon:'✉',title:'Direct delivery',description:'Bug reports and suggestions are sent to the STORMWATCH project inbox through the configured email provider.'}]},
    {version:'0.10.1', date:'2026-10-15', title:'Pre-release testing signup', subtitle:'Join the STORMWATCH test group and send feedback before public release.', changes:[{icon:'↗',title:'Tester signup',description:'New signup form collects an email address and optional testing interests, with consent and validation.'},{icon:'✉',title:'Private delivery',description:'Signup emails can be delivered securely through Resend when configured in Vercel. No secret API keys are exposed in the browser.'}]},
    {version:'0.10.0', date:'2026-10-15', title:'Clearer map & advisory age', subtitle:'A larger live map, transparent timestamps, and simpler historical inspection.', changes:[{icon:'▣',title:'More room for the map',description:'Removed the fixed timeline from the live and archive workspaces, including the redundant mobile Replay control.'},{icon:'◷',title:'Storm advisory age',description:'Delayed and stale systems now show elapsed time since the actual NHC advisory issue time, refreshed while the dashboard is open.'},{icon:'↔',title:'Archive navigation preserved',description:'Historical observations remain selectable on the map and now have Previous and Next controls in the inspector.'}]},
    {version:'0.9.9', date:'2026-10-15', title:'Project support & continental radar default', subtitle:'A way to support the independent STORMWATCH project, with CONUS selected by default for NWS radar.', changes:[{icon:'↗',title:'Support STORMWATCH',description:'A visible Support link on desktop and mobile opens the project donation page in a separate tab.'},{icon:'▧',title:'CONUS radar by default',description:'The NWS radar region now begins on Continental US; Gulf, Southeast and Caribbean choices remain available.'},{icon:'⌖',title:'Geographic alignment retained',description:'Radar continues using geographic EPSG:4326 bounds and existing map projection transforms.'}]},
    {version:'0.9.8', date:'2026-10-15', title:'Tropical Briefing source reliability', changes:['Added official NHC and NASA fallback feeds alongside Google News.','Expanded recent coverage and improved news-source availability reporting.','Avoid caching empty headline responses after temporary provider failures.']},
    {version:'0.9.7', date:'2026-10-15', title:'Daily tropical news briefing', subtitle:'Source-linked tropical news with an optional daily AI summary, available from the top navigation.', changes:[{icon:'▤',title:'Tropical Briefing',description:'A dedicated page collects recent cyclone and hurricane research headlines, linking every item to its source.'},{icon:'◎',title:'Optional AI synthesis',description:'An OpenAI-backed summary is available after the site owner configures OPENAI_API_KEY in Vercel; the secret stays on the server.'},{icon:'◷',title:'Daily caching',description:'Briefing is calculated per UTC day when accessed; production persistence requires external storage.'}]},
    {
      version:'0.9.5', date:'2026-10-15', title:'Map performance hotfix',
      subtitle:'Faster startup with offline coastline detail by default, smoother map interaction, and fewer background requests.',
      changes:[
        {icon:'◇',title:'Detail off at launch',description:'The map initially uses bundled coastlines without requesting OpenStreetMap tiles. Switch Detail On anytime for roads and town labels.'},
        {icon:'⌖',title:'Smoother movement',description:'Map dragging and wheel zoom schedule canvas updates once per animation frame instead of painting repeatedly per input event.'},
        {icon:'◷',title:'Lighter background activity',description:'Auxiliary data requests are deferred briefly at startup, and periodic refreshes pause while the tab is hidden.'},
        {icon:'▤',title:'Mobile rendering optimization',description:'Caps high-density canvas scaling on smaller screens and reduces stored map-tile memory.'}
      ]
    },
    {
      version:'0.9.4', date:'2026-10-15', title:'Operations console refinement & About page',
      subtitle:'A focused storm monitoring workspace, creator profile, and release notes visible whenever the site opens.',
      changes:[
        {icon:'◫',title:'Refined operational interface',description:'Updated navigation, panel hierarchy, typography, and map controls without changing data-provider behavior.'},
        {icon:'◎',title:'About STORMWATCH',description:'Added a creator profile covering UAS studies, meteorology, and hurricane research using observations from tropical systems.'},
        {icon:'↗',title:'What’s New at startup',description:'The release dialog now opens on every new page load and remains available from the header.'},
        {icon:'▤',title:'Mobile layout preserved',description:'Retains map-first viewing and slide-up navigation from the v0.9.3 mobile update.'}
      ]
    },
    {
      version:'0.9.3', date:'2026-10-15', title:'Mobile operations layout',
      subtitle:'Phone-first globe viewing, bottom navigation and touch-friendly storm intelligence.',
      changes:[
        {icon:'⌖', title:'Map-first mobile dashboard', description:'The globe fills the phone screen instead of being pushed below two columns of controls.'},
        {icon:'▧', title:'Bottom navigation and slide-up workspaces', description:'Storms, models, weather, layers, reconnaissance and intelligence open only when needed.'},
        {icon:'↔', title:'Touch controls and compact replay', description:'Larger buttons, pinch-to-zoom, horizontal map-toolbar scrolling, and a collapsible replay timeline.'}
      ]
    },
    {
      version:'0.9.2', date:'2026-10-14', title:'Radar map alignment & freshness correction',
      subtitle:'Corrects radar geographic positioning and avoids showing stale echoes as current weather.',
      changes:[
        {icon:'⌖', title:'Radar positioning corrected', description:'Preserves the NOAA raster geographic extent in both map modes, correcting a possible several-degree offset in earlier builds.'},
        {icon:'◷', title:'Stale radar is hidden', description:'Old radar feeds are no longer drawn as if they represent current conditions; the Weather panel reports why.'},
        {icon:'◉', title:'Echoes are not surface rainfall', description:'Clarified the radar labels and added a direct NWS radar cross-check for rain/no-rain disagreements.'}
      ]
    },
    {version:'0.9.1', title:'Version and changelog popup', changes:[
      'Introduced the automatically shown What’s New dialog with per-version dismissal memory.',
      'Added expandable previous release notes and a What’s New button in the top bar.'
    ]},
    {version:'0.9', title:'UI redesign & GOES preview fix', changes:[
      'Reorganized the sidebar into Storms, Models, Weather, Layers, and Recon workspaces.',
      'Constrained GOES image previews to the panel with a separate bounded enlarge view.',
      'Improved focus controls, chart placement, responsiveness, and archive-mode hiding.'
    ]},
    {version:'0.8', title:'Forecast model comparison', changes:[
      'Added NHC public ATCF forecast-aid parsing and same-cycle track/intensity comparisons.',
      'Added HAFS-A/B, GFS, ECMWF and AI-model identifiers where actual records are published.',
      'Added model track overlays, wind/pressure charts, and CSV exports; unsupported guidance remains unavailable.'
    ]},
    {version:'0.7', title:'More detailed maps & satellite layer beta', changes:[
      'Introduced zoom-dependent OpenStreetMap roads, cities, towns, and place labels in 2D and globe modes.',
      'Added an optional source-checked NOAA satellite-map beta layer and preserved the offline coastline fallback.'
    ]},
    {version:'0.6', title:'Aircraft sightings & cleaner archives', changes:[
      'Added public ADS-B sightings for selected NOAA research aircraft and optional TEAL callsign lookup.',
      'Made live radar, satellite, aircraft, and forecast controls disappear during archive replay.'
    ]},
    {version:'0.5', title:'Radar & reconnaissance', changes:[
      'Added a georeferenced NOAA/NWS MRMS radar image layer with recent-time and opacity controls.',
      'Improved reconnaissance bulletin matching and source age/status indicators.'
    ]},
    {version:'0.4', title:'Automatic data checks & GOES preview', changes:[
      'Added scheduled NHC updates and dashboard notification of source changes.',
      'Added NOAA GOES satellite previews and acquisition-time/freshness reporting.'
    ]},
    {version:'MVP', title:'Initial hurricane viewer', changes:[
      'Introduced the interactive globe, historical storm replay, basic NHC adapters, HDOB observation viewer, and UAS CSV import.'
    ]}
  ];
  const latest = RELEASES[0];
  const backdrop = document.getElementById('releaseDialogBackdrop');
  const dialog = backdrop?.querySelector('[role="dialog"]');
  const openButton = document.getElementById('openReleaseNotes');
  const closeButton = document.getElementById('releaseDialogClose');
  const enterButton = document.getElementById('releaseEnter');
  if (!backdrop || !dialog || !openButton || !closeButton || !enterButton) return;

  const latestItems = document.getElementById('releaseLatestItems');
  const historyList = document.getElementById('releaseHistoryList');
  const makeNode = (tag, className, text) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  };
  document.getElementById('releaseCurrentVersion').textContent = `v${latest.version}`;
  document.getElementById('releaseDate').textContent = latest.date;
  document.getElementById('releaseIntro').textContent = latest.subtitle;
  for (const change of latest.changes) {
    const row = makeNode('div','release-change');
    row.append(makeNode('span','release-change-icon',change.icon));
    const details = makeNode('div');
    details.append(makeNode('strong','',change.title), makeNode('p','',change.description));
    row.append(details);
    latestItems.append(row);
  }
  for (const release of RELEASES.slice(1)) {
    const item = makeNode('details');
    const summary = makeNode('summary');
    summary.append(makeNode('strong','',release.version === 'MVP' ? 'MVP' : `v${release.version}`),makeNode('em','',release.title));
    const list = makeNode('ul');
    for (const note of release.changes) list.append(makeNode('li','',note));
    item.append(summary,list);
    historyList.append(item);
  }

  let previouslyFocused = null;
  let didSetInert = false;
  let open = false;
  function dismissedVersion() {
    try { return window.localStorage.getItem(STORAGE_KEY); } catch { return null; }
  }
  function rememberDismissal() {
    try { window.localStorage.setItem(STORAGE_KEY, latest.version); } catch { /* Works without storage; seen status cannot persist. */ }
  }
  function showReleaseNotes() {
    if (open) return;
    previouslyFocused = document.activeElement;
    backdrop.hidden = false;
    open = true;
    const app = document.getElementById('app');
    if (app && !app.inert) { app.inert = true; didSetInert = true; }
    closeButton.focus();
  }
  function hideReleaseNotes() {
    if (!open) return;
    backdrop.hidden = true;
    open = false;
    rememberDismissal();
    const app = document.getElementById('app');
    if (app && didSetInert) { app.inert = false; didSetInert = false; }
    const focusTarget = previouslyFocused instanceof HTMLElement ? previouslyFocused : openButton;
    if (focusTarget && focusTarget.isConnected && typeof focusTarget.focus === 'function') focusTarget.focus();
    else openButton.focus();
  }
  document.getElementById('releaseFeedback')?.addEventListener('click', () => { hideReleaseNotes(); document.querySelector('[data-open-testers]')?.click(); });
  openButton.addEventListener('click', showReleaseNotes);
  closeButton.addEventListener('click', hideReleaseNotes);
  enterButton.addEventListener('click', hideReleaseNotes);
  backdrop.addEventListener('click', (event) => { if (event.target === backdrop) hideReleaseNotes(); });
  document.addEventListener('keydown', event => {
    if (!open) return;
    if (event.key === 'Escape') { event.preventDefault(); hideReleaseNotes(); return; }
    if (event.key !== 'Tab') return;
    const focusable = [...dialog.querySelectorAll('button:not([disabled]),a[href],summary,[tabindex]:not([tabindex="-1"])')]
      .filter(el => el.getClientRects().length > 0);
    if (!focusable.length) { event.preventDefault(); dialog.focus(); return; }
    const i = focusable.indexOf(document.activeElement);
    if (event.shiftKey && (i <= 0)) { event.preventDefault(); focusable[focusable.length - 1].focus(); }
    else if (!event.shiftKey && (i === focusable.length - 1 || i < 0)) { event.preventDefault(); focusable[0].focus(); }
  });
  // Product requirement: present changes at every new page load, regardless of prior dismissal.
  showReleaseNotes();
})();
