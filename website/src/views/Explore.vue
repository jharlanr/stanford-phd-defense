<template>
  <div class="explore" :class="[`mode-${appMode}`, { 'with-landmarks': appMode === 'section' && !!landmarkData }]">
    <Globe
      :clicks="globeClicks"
      :greenland-hoverable="appMode === 'intro'"
      :show-arrows="showArrows"
      :rollback="rollbackProgress"
      :camera-tilt="cameraTilt"
      :stage-fit="appMode === 'menu' ? MENU_STAGE_FIT : null"
      :stage-fit-hold="stageFitHold"
      :chapter-focus="chapterFocus"
      :lake-overlay="lakeOverlay"
      :chapter-reveal="chapterReveal"
      :lake-polygons="lakePolygons"
      :lake-cutaway="lakeCutaway"
      :velocity-mode="velocityMode"
      :chapter-overlay="chapterOverlay"
      :slab-fx="slabFx"
      :chapter-exag="chapterExag"
      :chapter-exag-ms="chapterExagMs"
      :strip-velocity="stripVelocity"
      :hillshade="hillshade"
      :fieldwork-patch="fieldworkPatch"
      :screen-anchors="screenAnchors"
      :lake-strip="lakeStrip"
      :featured-pulse-id="featuredPulseId"
      :sim-domain="globeSimDomain"
      :sim-lake-highlight="ch2PhaseHoverNum ?? ch2BedLit"
      :sim-bc="ch2SimBc"
      :paused="((showTwinGlobes || ch1TwinsClosing) && !twinsLinger) || ch2SlabCover"
      :covered="introMapCovering && currentSection === 'introduction'"
      @greenland-click="beginTour"
      @lake-beacon-click="onLakeBeaconClick"
      @lake-beacon-hover="featuredHoverId = $event"
      @canvas-blank-click="onCanvasBlankClick"
      @sim-lake-hover="ch2LakeHover = $event"
      @sim-lake-pick="ch2LakePin = $event"
    />

    <!-- Drainage-class legend — Beat 0's key to the five colored,
         hoverable lakes (ESSD fig-4 classes + colors). Interactive:
         hovering a row pulses that lake on the globe; clicking a row
         opens its season video (same as clicking the lake). -->
    <DrainageLegend
      :visible="showDrainageLegend"
      @hover="featuredPulseId = $event"
      @select="onLakeBeaconClick"
    />

    <!-- The chapter's title card — "Chapter 1: <its thesis title>" in the
         top-left corner, on a chapter's landing beat only; the first NEXT
         drops it (ChapterTitleCard.vue). -->
    <ChapterTitleCard
      :show="showChapterCard"
      :chapter="chapterCardText.label"
      :title="chapterCardText.title"
      :side="chapterCardText.side"
      :status="chapterCardText.status"
      :venue="chapterCardText.venue"
    />

    <!-- Lake video popup — RIGHT-HALF DOCK (not modal), shown when the
         user clicks ANY of the five featured drainage-class lakes on
         Ch.1 Beat 0. Plays that lake's 2019 Sentinel-2 time-series.
         KEYED by lake id: switching lakes remounts the popup so the
         sidecar (class accent, curve, ticks) always matches the video. -->
    <LakeVideoPopup
      v-if="lakeVideo"
      :key="lakeVideo.id"
      :src="lakeVideo.src"
      :sidecar-url="lakeVideo.sidecarUrl"
      :title="lakeVideo.title"
      :lake-id="lakeVideo.id"
      @close="lakeVideo = null"
    />

    <!-- "Where does the water go?" — in-canvas button anchored below
         North Lake (via window.__nlBeaconScreen). Visible only while
         the NORTH LAKE video is open (it launches the hydrofracture
         cross-section story — the other lakes' popups just close);
         clicking it advances Ch.1 AND dismisses the popup in one go. -->
    <WaterPathButton
      v-if="showWaterPathButton"
      @click="advanceToCrossSection"
    />

    <!-- Beat-anchored slab action buttons:
         each rides the fracture anchor (window.__slabFracScreen). -->
    <SlabActionButton
      v-if="ch1BeatIs(ch1First('reveal'))"
      label="Drain the lake"
      arrow="↓"
      placement="above"
      @click="bumpCh1Advance"
    />
    <SlabActionButton
      v-if="ch1BeatIs(ch1First('drain'))"
      label="How does the ice respond?"
      arrow="→"
      placement="right"
      @click="bumpCh1Advance"
    />
    <SlabActionButton
      v-if="ch1BeatIs(ch1First('paint'))"
      label="Toy model"
      arrow="→"
      placement="right"
      @click="bumpCh1Advance"
    />

    <!-- τxx colour scale — a horizontal bar beneath the object while
         the Elmer paint is on the cross-section (beat 3), plus the
         bottom-right [Elmer/Ice · Gagliardini et al. 2013] reference
         link. (The beats 1–2 cross-section stats card is gone — the
         director found it unnecessary.) -->
    <StressLegend :visible="showStressLegend" />

    <!-- Theory panel — full-screen math mode for Ch.1's derivation
         beats. Mounted one beat EARLY (hidden on the paint beat) so its heavy
         first paint — full-screen SVG + field image decode — happens
         BEFORE the seam handoff; the beat 3→4 entry is then a cheap
         opacity tween over the camera-fit slab. -->
    <TheoryPanel
      v-if="currentSection === 'chapter1' && ch1Beat >= ch1First('paint')"
      :stage="theoryStage ?? 0"
      :hidden="theoryStage === null"
      :entry-fx="theoryEntryFx"
    />

    <!-- TWIN GLOBES — Ch.1's closing beat: two live 3D Greenlands, the
         ACL painted on the left one, max surface stress on the right,
         orbit-synced. Mounted one beat EARLY (hidden behind the theory
         panel) so its textures decode before the user arrives. -->
    <TwinGlobes
      v-if="(currentSection === 'chapter1' && ch1Beat >= ch1First('maps') && twinsMountReady) || twinsLinger"
      :active="showTwinGlobes || ch1TwinsClosing || twinsLinger"
      :closing="ch1TwinsClosing"
      :linger="twinsLinger"
      :class="{ 'twins-linger': twinsLinger }"
      @closed="onTwinsClosed"
    />

    <!-- "Zoom in" — Ch.2 Beat 0, floats above the lake whose imagery
         popup is open; clicking launches that lake's zoom/carve beat. -->
    <DrainLakeButton
      v-if="currentSection === 'chapter2' && ch2PhaseNow === CH2_PHASE.lakes && lakeVideo"
      :lake-id="lakeVideo.id"
      @click="drainSelectedLake"
    />

    <!-- "Drain the lake" over the MGSIM page's landed block (its own
         two-step). Chapter 2 dropped it for the
         PRE / POST / DIFFERENCE tier below. -->
    <DrainDomainButton
      v-if="simLanded && isMgsimPage"
      @click="onDrainDomainClick"
    />

    <!-- Ch.2's block controls: PRE DRAINAGE ·
         POST DRAINAGE · DIFFERENCE, then IMAGERY · ELASTIC MODEL · VISCOUS
         MODEL once a stage is picked, with the two Sentinel-2 dates as a
         small figure label. State: config/ch2State.ts (ch2View).
         The director asked that the buttons stay up through the chapter's
         NEXT clicks, doubling as headings for what is on screen in the
         imagery and stress spaces: lit to the view on screen. A later
         request made any button clickable on any centre lake, to see the
         same views of the stress space unified across all centre lakes:
         controls on EVERY station beat (imagery + results, both passes,
         any lake) — a click sets ch2View (the station override,
         config/ch2State.ts); NEXT / BACK walk the beats whatever was
         picked. -->
    <SimViewControls
      v-if="ch2ControlsOn && !ch2BcFocus"
      :stage="ch2View.stage"
      :layer="ch2View.layer"
      :date-pre="ch2Dates?.pre ?? null"
      :date-post="ch2Dates?.post ?? null"
      @pick="onCh2Pick"
    />

    <!-- Stress popout (docked top-center): hover or
         click a catalog lake on the block → its in-polygon σ_t1/σ_t2
         table. The MGSIM page only: Chapter 2 does not need the per-lake
         details on a polygon hover, so the card went there — the hover
         highlight stays. -->
    <SimLakeCard
      v-if="simDrained && isMgsimPage"
      :lake="ch2LakeHover ?? ch2LakePin"
      :pinned="ch2LakePin !== null && ch2LakeHover === null"
      :face="ch2Face"
      :model-label="isMgsimPage ? mgsimUi?.cardLabel : undefined"
    />

    <!-- Phase-space diagram (full-height right
         column, fixed ±500 kPa axes). Hover syncs with the block's
         outlines both ways. The MGSIM page only: Chapter
         2's stations show the walk's single stress space on every station
         beat (Ch2Results), never these two stacked panels. -->
    <PhaseSpacePanel
      :reserve-bottom="currentSection === 'chapter2'"
      :visible="isMgsimPage && !!mgsimUi?.phaseVisible"
      :model="isMgsimPage ? 'viscous' : ch2FaceModel"
      :center-num="ch2CenterNum"
      :highlight-num="ch2HighlightNum"
      :data-url="isMgsimPage ? mgsimPhaseUrl : undefined"
      :model-key="isMgsimPage ? mgsimUi?.phaseKey : undefined"
      :ghost-keys="isMgsimPage ? mgsimUi?.ghostKeys : undefined"
      :label="isMgsimPage ? mgsimUi?.phaseLabel : undefined"
      @lake-hover="ch2PhaseHoverNum = $event"
    />

    <!-- Chapter 2 · RESULTS + IMPLICATIONS (beats 3–9): one stress
         space at a time beside the painted
         block, then the flat comparison / complete / implications pages.
         Hover syncs with the block's outlines through ch2PhaseHoverNum,
         exactly as the beat-2 panel does. -->
    <Ch2Results
      v-if="appMode === 'section' && currentSection === 'chapter2' && ch2PhaseNow >= CH2_PHASE.pre"
      :beat="ch2Beat"
      :step="ch2BcOn ? null : ch2Single"
      :lake-id="ch2ActiveLake"
      :center-num="ch2CenterNum"
      :highlight-num="ch2HighlightNum"
      @lake-hover="ch2PhaseHoverNum = $event"
    />

    <!-- Shared ±1 MPa response colorbar — visible once a model is
         draped; names the active model (on the results walk: the beat's
         model and principal). -->
    <BlisterStressLegend
      v-if="!isMgsimPage"
      :visible="(simDrained && (ch2Face === 'elastic' || ch2Face === 'viscous')) || ch2Single !== null"
      :model="ch2Single?.model ?? ch2FaceModel"
      :field="ch2Single ? (ch2Single.field === 'pre' ? 'nopatch' : ch2Single.field === 'post' ? 'patch' : 'difference') : ch2Field"
      :comp="ch2Single?.comp ?? 't1'"
    />
    <!-- …and the bed beat's key (the second center lake's walk): the
         glassy block's hypsometric bed + the neighbour lit gold. -->
    <Ch2BedLegend
      v-if="currentSection === 'chapter2'"
      :visible="ch2PhaseNow === CH2_PHASE.bed || ch2PhaseNow === CH2_PHASE.teaser"
      :palette-url="CH2_BED_PALETTE_URL"
      :vmin="ch2BedRangeNow[0]"
      :vmax="ch2BedRangeNow[1]"
      :lit-num="ch2BedLit"
    />
    <!-- …and its imagery twin: the IMAGERY · DIFFERENCE cell's scale. -->
    <SimImageryDiffLegend
      v-if="currentSection === 'chapter2'"
      :visible="simDrained && ch2ImgDiff"
    />
    <!-- …and the centre-lakes inset: top-left on every
         block beat — which of the seven the block is. -->
    <Ch2CenterLakesMap
      v-if="currentSection === 'chapter2'"
      :visible="ch2IsBlockPhase(ch2PhaseNow) && !ch2BcOn"
      :center-num="ch2CenterNum"
      @pick="onCh2InsetPick"
    />
    <!-- …and the ICE FLOW arrow just above the block's upper-left edge,
         beside them (the director wanted the ice-flow arrow near the
         mini map) — the Globe's 3D arrow stays the MGSIM page's.
         The imagery + results beats: on the bed and teaser beats' steep
         views the block runs up under the inset — no room beside it. -->
    <Ch2FlowArrow
      v-if="currentSection === 'chapter2'"
      :visible="(ch2IsImageryPhase(ch2PhaseNow) || ch2IsResultsPhase(ch2PhaseNow)) && !ch2BcOn"
    />

    <!-- Bottom-right cards (the corner the director chose for all such
         cards): the bed-ensemble door (lake 1951 only — its ensemble) and
         SEE MORE FIELDS → the chapter's deeper-dive page. The block's own beats
         only: the results walk owns the right column and the page. -->
    <SimBlockCards
      v-if="currentSection === 'chapter2' && ((ch2IsImageryPhase(ch2PhaseNow) && !ch2Single) || ch2PhaseNow === CH2_PHASE.teaser)"
      :ensemble="ch2PhaseNow === CH2_PHASE.teaser && ch2ActiveLake === 'CW2019_1951'"
      :fields="ch2PhaseNow !== CH2_PHASE.teaser"
      @ensemble="openEnsembleFromCh2"
    />
    <!-- …and the teaser's figure labels: which bed is on both blocks, the
         cycle's pips, the twin's ±400 kPa key (Ch2Teaser.vue). -->
    <Ch2Teaser
      v-if="currentSection === 'chapter2'"
      :state="ch2PhaseNow === CH2_PHASE.teaser ? ch2Teaser : null"
    />
    <!-- Chapter 2 · THEORY: the idealized slab — Elmer/
         Ice against the shallow-stream theory (config/ch2Beats.ts `slab` ·
         `slab-da` · `slab-compare`). Its own opaque layer + WebGL canvas
         above the globe (paused under it, like Chapter 1's twins). Mounted
         from the bed beat on, so its shaders and the current run's textures
         are on the GPU before NEXT can reach it. -->
    <Ch2Slab
      v-if="appMode === 'section' && currentSection === 'chapter2' && ch2PhaseNow >= CH2_PHASE.bed"
      :beat="ch2Beat"
      @advance="navNext"
      @transit-done="onSlabTransitDone"
      @covering="ch2SlabCover = $event"
    />

    <!-- Boundary conditions: the
         bottom-left toggle. The camera steps back to the whole 24.75 km
         model domain (the Globe's ghost shell) and one card per
         boundary labels it; a card click flies head-on to that boundary
         (chapterFocus) and the Globe draws its overlay there. -->
    <SimBcButton
      v-if="currentSection === 'chapter2' && (simLanded || simDrained)"
      :active="ch2BcOn"
      @toggle="ch2BcOn = !ch2BcOn"
    />
    <SimBcCards
      v-if="currentSection === 'chapter2' && (simLanded || simDrained)"
      :active="ch2BcOn"
      :model="ch2FaceModel"
      :focus="ch2BcFocus"
      :lake-id="ch2ActiveLake"
      @focus="ch2BcFocus = $event"
      @hover="ch2BcHover = $event"
    />

    <!-- THE site's back/next — ONE pair of pills, on EVERY page, same
         spot, same size, same font (the director wanted BACK and NEXT
         always present, so that the visitor has a deterministic path
         through the website). Pinned top-right beside
         the top nav (below it under 1840 px). Beat pages (Introduction,
         chapters) step their beats first; the path between pages is
         config/sitePath.ts. Labels: "next" / "back", a chapter's short
         name when next leaves for it ("Ch. 2"), "menu" at the two ends. -->
    <div v-if="appMode === 'section' && currentSection" class="beat-nav">
      <button class="beat-btn beat-btn-back" @click="navBack">
        ← {{ navBackLabel }}
      </button>
      <button class="beat-btn beat-btn-next" @click="navNext">
        {{ navNextLabel }} →
      </button>
    </div>

    <!-- Inset zoom window — paired with the bronze scale arrow on
         Greenland's cross-section, shows the ice column thickness as
         a stack of 6 procedural OWTCs in its own 3D scene. Mounted
         only in Introduction step 0 so it doesn't burn GPU elsewhere. -->
    <InsetZoom
      v-if="currentSection === 'introduction'"
      :progress="rollbackProgress"
    />

    <!-- Scale-reference card (top-left): flat USA basemap with
         Greenland's silhouette overlaid in gold at correct relative
         scale. Two stacked silhouettes (a black-outline shadow behind
         the gold fill) so Greenland reads with a clean dark border
         against the USA imagery. -->
    <div
      v-if="currentSection === 'introduction'"
      class="scale-reference"
      :style="{ opacity: scaleReferenceOpacity }"
    >
      <div
        class="scale-reference-frame"
        :style="{ '--silhouette-url': `url(${silhouetteUrl})` }"
      >
        <img class="usa-image" :src="usaBasemapSrc" alt="USA reference" />
        <div class="greenland-silhouette greenland-outline" />
        <div class="greenland-silhouette greenland-fill" />
      </div>
      <div class="scale-reference-caption">Greenland Size Comparison</div>
    </div>

    <!-- INTRO: spinning globe + title. Greenland itself is the button
         — hovering glows it gold + black-outlined; clicking begins the
         tour. The hint below the title tells users what to do.
         (Plus: easter eggs eventually live on the spinning globe.) -->
    <Transition name="intro-fade">
      <div v-if="appMode === 'intro'" class="intro-overlay">
        <!-- The dissertation title, verbatim from the thesis
             main.tex \title (the director's rule: the thesis title is the
             title). The colon is the line break; the caps come from CSS so
             the text stays a normal sentence for search, tabs and screen
             readers. -->
        <h1 class="intro-title">
          <span class="intro-title-line">Greenland Supraglacial Lake Drainage Events:</span>
          <span class="intro-title-line">Modeling and Observations</span>
        </h1>
        <p class="intro-sub">
          PhD Defense · Josh Rines · Stanford Geophysics · October 9, 2026
        </p>
        <p class="intro-hint">Click on Greenland to begin.</p>

        <!-- Sponsor / affiliation logos. Click opens link in new tab.
             SDSS amended to preserve Stanford cardinal "Stanford" with
             light off-white "| Doerr / School of Sustainability" so
             the brand reads against the dark page. -->
        <div class="logo-row">
          <a
            class="logo-link logo-link-sdss"
            href="https://sustainability.stanford.edu/"
            target="_blank"
            rel="noopener noreferrer"
            title="Stanford Doerr School of Sustainability"
          >
            <img :src="logoSdssSrc" alt="Stanford Doerr School of Sustainability" />
          </a>
          <a
            class="logo-link"
            href="https://icyphysics.stanford.edu/"
            target="_blank"
            rel="noopener noreferrer"
            title="Icy Physics @ Stanford"
          >
            <img :src="logoIcyphysicsSrc" alt="Icy Physics" />
          </a>
          <a
            class="logo-link"
            href="https://mineralx.stanford.edu/"
            target="_blank"
            rel="noopener noreferrer"
            title="Mineral-X @ Stanford"
          >
            <img :src="logoMineralxSrc" alt="Mineral-X" />
          </a>
          <a
            class="logo-link"
            href="https://www.nsf.gov/geo/opp"
            target="_blank"
            rel="noopener noreferrer"
            title="NSF Office of Polar Programs"
          >
            <img :src="logoNsfSrc" alt="NSF" />
          </a>
        </div>

        <!-- The author's own links, top-right — the logo strip's
             treatment in the opposite corner (monochrome on dark, hover
             lifts one and dims the rest). Fades with the intro chrome. -->
        <div class="persona-row">
          <a
            v-for="l in PERSONAL_LINKS"
            :key="l.id"
            class="persona-link"
            :class="`persona-link-${l.id}`"
            :href="l.href"
            target="_blank"
            rel="noopener noreferrer"
            :title="l.label"
            :aria-label="l.label"
          >
            <svg v-if="l.id === 'linkedin'" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
            </svg>
            <svg v-else-if="l.id === 'github'" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
            </svg>
            <img v-else class="persona-avatar" :src="AVATAR_URL" alt="" />
          </a>
        </div>
      </div>
    </Transition>

    <!-- "Return to globe" — pinned to viewport top-left when the user
         is in menu mode, separate from the right-side menu panel so the
         menu itself can be tighter (no header chrome inside the panel). -->
    <Transition name="menu-fade">
      <button
        v-if="appMode === 'menu'"
        class="menu-back-floating"
        @click="returnToGlobe"
      >
        ← Return to globe
      </button>
    </Transition>

    <!-- MENU: vertical golden cards on the right. No chrome, no hint
         line (visitors know what a menu is for). All 5 fit
         without scroll. Cards + thumbs come straight from the section
         registry. -->
    <Transition name="menu-fade">
      <aside v-if="appMode === 'menu'" class="menu-panel">
        <div class="menu-list">
          <MenuCard
            v-for="s in primarySections"
            :key="s.id"
            :label="s.label"
            :subtitle="s.subtitle"
            :status="s.status"
            :venue="s.venue"
            @select="selectSection(s.id)"
          >
            <template #thumb="{ playing, lit }">
              <component :is="s.thumb" v-if="s.thumb" :playing="playing" :lit="lit" />
            </template>
          </MenuCard>
        </div>
        <div class="menu-aux">
          <template v-for="(s, i) in auxSections" :key="s.id">
            <span v-if="i > 0 && auxSections[i - 1].group !== s.group" class="menu-aux-sep" aria-hidden="true" />
            <button
              class="menu-aux-btn"
              @click="selectSection(s.id)"
            >{{ s.label }}</button>
          </template>
        </div>
      </aside>
    </Transition>

    <!-- TOP NAV: replaces the menu after first section selection. The
         leftmost button is "Menu" — returns to the vertical-menu state
         so the user can browse from the top of the tree again. -->
    <Transition name="topnav-fade">
      <!-- The wrapper is exactly the ribbon's box, so the sub-menu hung
           under it can span the ribbon's middle 75 % in plain CSS — and,
           as the ribbon's SIBLING, its own backdrop blur sees the scene
           (a backdrop-filter child of the ribbon would only see the
           ribbon). -->
      <div v-if="appMode === 'section'" class="top-nav-wrap">
        <nav class="top-nav">
          <button class="nav-btn nav-back" @click="returnToMenu" title="Back to main menu">
            ☰
          </button>
          <!-- A bar where the thesis ends and the rest begins —
               drawn wherever the registry's `group` changes. Bare names
               only (the director wanted plain "Chapter 1" and so on here,
               no venue or stage tags); the menu cards keep venue + stage. -->
          <template v-for="(s, i) in navSections" :key="s.id">
            <span v-if="i > 0 && navSections[i - 1].group !== s.group" class="nav-sep" aria-hidden="true" />
            <button
              class="nav-btn"
              :class="{ active: currentSection === s.id }"
              @click="selectSection(s.id)"
            >{{ s.label }}</button>
          </template>
        </nav>
        <!-- The section's sub-menu: its landmark beats as notches on a
             rule under the ribbon's middle 75 % (config/landmarks.ts).
             A plain crossfade, NOT out-in: during a cross-section BACK
             (Ch.2 → Ch.1) the leaving bar's transition never completed
             and out-in then never let the new bar enter;
             the bar is absolutely positioned, so both can overlap. -->
        <Transition name="landmarks-fade">
          <BeatLandmarks
            v-if="landmarkData"
            :key="beatChapter ?? ''"
            :data="landmarkData"
            :beat="landmarkBeat"
            @jump="jumpToBeat"
          />
        </Transition>
      </div>
    </Transition>

    <!-- The Introduction is HEADLESS too (no title, no
         prose): its steps are driven by the shared pills; it paints only
         figure labels (step 0's measuring lines + sea-level number) and a
         corner reference link. -->
    <SectionMotivation
      v-if="appMode === 'section' && currentSection === 'introduction'"
      :advance-trigger="introAdvanceTrigger"
      :back-trigger="introBackTrigger"
      :jump-to="beatJump"
      @beat-change="onIntroBeatChange"
      @screen-anchors="screenAnchors = $event"
      @globe-clicks="onGlobeClicks"
      @show-arrows="onShowArrows"
      @rollback-progress="onRollbackProgress"
      @timeline-step="onTimelineStep"
      @timeline-paper="introTimelinePaper = $event"
      @timeline-focus="introTimelineFocus = $event"
      @chapter-focus="onChapterFocus"
      @chapter-exag="onChapterExag"
      @chapter-exag-ms="chapterExagMs = $event"
      @strip-velocity="stripVelocity = $event"
      @hillshade="hillshade = $event"
      @fieldwork-patch="fieldworkPatch = $event"
      @fieldwork-layer="introFieldwork = $event"
      @season-view="introSeasonView = $event"
      @advance="advanceSection"
    />

    <!-- Ch.1 is HEADLESS: no side panel — the presenter narrates and
         the beat-nav pills (top-right) + in-canvas buttons drive it.
         Mounted outside the aside so no invisible panel eats clicks. -->
    <SectionCh1
      v-if="appMode === 'section' && currentSection === 'chapter1'"
      :advance-trigger="ch1AdvanceTrigger"
      :back-trigger="ch1BackTrigger"
      :jump-to="beatJump"
      :reveal-trigger="ch1RevealTrigger"
      @advance="onCh1AdvanceRequest"
      @chapter-focus="onChapterFocus"
      @lake-overlay="onLakeOverlay"
      @lake-polygons="onLakePolygons"
      @lake-cutaway="lakeCutaway = $event"
      @velocity-mode="onVelocityMode"
      @rollback-progress="onRollbackProgress"
      @globe-clicks="onGlobeClicks"
      @chapter-exag="onChapterExag"
      @chapter-reveal="onChapterReveal"
      @slab-fx="onSlabFx"
      @theory-stage="onTheoryStage"
      @theory-entry-fx="onTheoryEntryFx"
      @beat-change="onCh1BeatChange"
    />

    <!-- Ch.2 is headless too: seven PNAS lakes,
         popup, and the drain-the-lake carve. -->
    <SectionCh2
      v-if="appMode === 'section' && currentSection === 'chapter2'"
      :advance-trigger="ch2AdvanceTrigger"
      :back-trigger="ch2BackTrigger"
      :jump-to="beatJump"
      :selected-lake-id="ch2SelectedLake"
      :second-lake-id="ch2SecondLake"
      :warm-lake-id="ch2PhaseNow === CH2_PHASE.lakes ? (lakeVideo?.id ?? null) : null"
      @advance="advanceSection"
      @open-lake="onLakeBeaconClick"
      @chapter-focus="onChapterFocus"
      @lake-polygons="onLakePolygons"
      @globe-clicks="onGlobeClicks"
      @chapter-exag="onChapterExag"
      @sim-domain="onSimDomain"
      @sim-dates="ch2Dates = $event"
      @beat-change="onCh2BeatChange"
      @teaser="ch2Teaser = $event"
    />

    <!-- Ch.3 (ESSD): headless like Ch.1/Ch.2 — beat 0
         is Ch.1's opening view with the five lakes' seasons in callout
         panels, beat 1 dives to the nadir map of the labeled population
         (the Globe's lakeStrip), then the IRR matrices and the
         walkthrough as opaque layers ABOVE the live Globe — never a veil
         on it (the sim-block landing stalls 30–60 s if the Globe is
         hidden — the compositor reads the WebGL canvas back every frame). -->
    <SectionCh3
      v-if="appMode === 'section' && currentSection === 'chapter3'"
      :advance-trigger="ch3AdvanceTrigger"
      :back-trigger="ch3BackTrigger"
      :jump-to="beatJump"
      :globe-hover-id="featuredHoverId"
      :globe-click="ch3LakeClick"
      @advance="advanceSection"
      @beat-change="onCh3BeatChange"
      @chapter-focus="onChapterFocus"
      @lake-polygons="onLakePolygons"
      @globe-clicks="onGlobeClicks"
      @chapter-exag="onChapterExag"
      @chapter-exag-ms="chapterExagMs = $event"
      @hillshade="hillshade = $event"
      @lake-strip="lakeStrip = $event"
      @lake-hover="featuredPulseId = $event"
    />

    <!-- Additional Work → MGSIM bed ensemble: headless for
         the globe like Ch.2 (same sim-domain block, landed on lake
         1951) and it renders its own pill row + data column. The Ch.2
         in-canvas pieces below are gated on simLanded/simDrained so
         they serve both pages. -->
    <SectionMgsim
      v-if="appMode === 'section' && isMgsimPage"
      :face="ch2Face"
      :advance-trigger="mgsimAdvanceTrigger"
      @exit="onMgsimExit"
      @ui-state="mgsimUi = $event"
      @chapter-focus="onChapterFocus"
      @lake-polygons="onLakePolygons"
      @globe-clicks="onGlobeClicks"
      @chapter-exag="onChapterExag"
      @sim-domain="onSimDomain"
      @sim-dates="ch2Dates = $event"
      @face-reset="setCh2View('post', 'imagery')"
      @beat-change="onMgsimBeatChange"
    />

    <!-- INTRODUCTION · the fly-along: the flat fieldwork map,
         a full-screen layer ABOVE the globe that takes over the dive's
         landing frame pixel-aligned. Mounted under the timeline layer so
         the timeline sits on top of it. `clip` = the clip step's GoPro
         clip (steps 5–7, config/introSteps.ts). NOTE: it is pre-mounted
         (hidden) from step 1 as a warm-up — the aside's pointer
         pass-through keys on `revealed`, not `active`, or step 1's NEXT
         stops taking clicks (this happened live once). -->
    <FieldworkExplorer
      v-if="currentSection === 'introduction' && introFieldwork?.active"
      mode="intro"
      :initial-view="introFieldwork.view"
      :revealed="introFieldwork.revealed"
      :basemap-src="introFieldwork.src"
      :clip="introFieldwork.clip"
      @covering="introMapCovering = $event"
    />

    <!-- INTRODUCTION · "Greenland flows" (step 1) and the seasons (2–3):
         the colour scale of the drape — up while the paint is (clicks 2,
         not stripped for the fly-along, not under the timeline). The
         anomaly step swaps in the diverging scale from the manifest (the
         speed step's monthly / multi-year brackets are gone). -->
    <VelocityColorbar
      :visible="currentSection === 'introduction' && globeClicks >= 2 && !stripVelocity && introTimelineStep === null"
      :anomaly="introSeasonView === 'anom' && seasonUi.manifest
        ? { stops: seasonUi.manifest.anomaly_colour.stops, lim: seasonUi.manifest.anomaly_colour.lim,
            grey: seasonUi.manifest.anomaly_colour.neutral_grey }
        : null"
    />

    <!-- INTRODUCTION · the literature timeline: a full-screen
         layer ABOVE the globe (never a veil on it), mounted for the
         Introduction's timeline steps. Sits before the section panel
         in DOM order so the panel's title row + next/back stay on top. -->
    <Transition name="section-fade">
      <LiteratureTimeline
        v-if="currentSection === 'introduction' && introTimelineStep !== null"
        :key="introTimelineStep"
        :revisit="introTimelineStep === 1"
        :walk="introTimelinePaper"
        :focus="introTimelineFocus"
      />
    </Transition>

    <!-- SECTION: per-section content panel on the right (only the stub
         pages now). The Introduction and Ch.1–3 are headless (above);
         the rest are flat layers. -->
    <Transition name="section-fade">
      <aside
        v-if="appMode === 'section' && currentSection &&
              currentSection !== 'introduction' &&
              currentSection !== 'chapter1' &&
              currentSection !== 'chapter2' && currentSection !== 'chapter3' &&
              currentSection !== 'additional-work' && currentSection !== 'repos' &&
              currentSection !== 'conclusion' && currentSection !== 'acknowledgements' &&
              currentSection !== 'references'"
        :key="currentSection"
        class="section-panel"
      >
        <!-- next-label null: the shared pills are the page's next. -->
        <SectionStub
          :section-id="currentSection"
          :label="sectionLabel"
          :next-label="null"
          @advance="advanceSection"
        />
      </aside>
    </Transition>


    <!-- ADDITIONAL WORK: a flat grid of cards, no globe.
         Each live card is a door to its own sub-route
         (/additional-work/<page>); MGSIM keeps the globe (above), the
         Terminal-Bench page is flat like this grid. -->
    <Transition name="section-fade">
      <SectionAdditionalWork
        v-if="appMode === 'section' && currentSection === 'additional-work' && (addlPage === null || addlPage === 'deeper')"
        :view="addlPage === 'deeper' ? 'deeper' : 'beyond'"
        :chapter="deeperChapter"
        @open="openAddlPage"
      />
    </Transition>
    <!-- Additional Work → the fieldwork explorer:
         the same map the Introduction lands on, in full mode (its own
         exit pill, default view). The old /extras side door redirects
         here. A flat opaque layer above the live globe, never a veil. -->
    <Transition name="section-fade">
      <FieldworkExplorer
        v-if="appMode === 'section' && isFieldworkPage"
        mode="full"
        :initial-view="null"
        :revealed="true"
        @exit="exitTo('additional-work')"
      />
    </Transition>
    <Transition name="section-fade">
      <SectionTerminalBench
        v-if="appMode === 'section' && isTbsPage"
        @exit="exitTo('additional-work')"
        @chapter3="openDoor('chapter3')"
        @chapter3-beat="(b: number) => router.push({ name: 'chapter3', query: { beat: String(b) } })"
      />
    </Transition>

    <!-- Additional Work → fracture / stream mapping:
         the AGU 2024 poster Iona Xia led. Flat opaque layer above the
         live globe, like the Terminal-Bench page. -->
    <Transition name="section-fade">
      <SectionFracture
        v-if="appMode === 'section' && isFracturePage"
        @exit="exitTo('additional-work')"
      />
    </Transition>

    <!-- Additional Work → "Label lakes yourself · the inter-rater 200":
         Chapter 3's label stage dealt as a deck of the
         ESSD inter-rater lakes, scored against the three labelers. Flat
         opaque layer above the live globe; nothing persists. -->
    <Transition name="section-fade">
      <SectionLabelLakes v-if="appMode === 'section' && isLabelPage" />
    </Transition>

    <!-- Additional Work → "Revisiting lake drainage papers":
         Christoffersen et al. 2018's cascade of 6–10 June 2010 on the ice,
         then every lake's own season of imagery. Like the MGSIM page it
         DRIVES the Globe (camera, exaggeration, the lake strip laid on the
         ice) and is a click-through layer above it — the Globe stays live
         and unveiled. The shared pills step its days while it says it has
         a step (`nav-state`). -->
    <Transition name="section-fade">
      <SectionRevisit
        v-if="appMode === 'section' && isRevisitPage"
        :advance-trigger="revisitAdvanceTrigger"
        :back-trigger="revisitBackTrigger"
        @nav-state="revisitNav = $event"
        @chapter-focus="onChapterFocus"
        @chapter-exag="onChapterExag"
        @chapter-exag-ms="chapterExagMs = $event"
        @hillshade="hillshade = $event"
        @globe-clicks="onGlobeClicks"
        @lake-strip="lakeStrip = $event"
      />
    </Transition>

    <!-- CONCLUSION: one page, the takeaways —
         a flat layer above the globe like the Repos table. -->
    <Transition name="section-fade">
      <SectionConclusion
        v-if="appMode === 'section' && currentSection === 'conclusion'"
        :advance-trigger="concAdvanceTrigger"
        :back-trigger="concBackTrigger"
        @beat-change="onConcBeatChange"
        @advance="advanceSection"
      />
    </Transition>

    <!-- ACKNOWLEDGEMENTS: the groups on one page, then one split-out step per
         group, then the full page again (SectionAcknowledgements). One route;
         ?beat=N deep-links a step. -->
    <Transition name="section-fade">
      <SectionAcknowledgements
        v-if="appMode === 'section' && currentSection === 'acknowledgements'"
        :advance-trigger="ackAdvanceTrigger"
        :back-trigger="ackBackTrigger"
        @beat-change="onAckBeatChange"
        @advance="advanceSection"
      />
    </Transition>

    <!-- REPOS: the software-repositories table —
         a flat layer above the globe like the Additional-Work grid. -->
    <Transition name="section-fade">
      <SectionRepos
        v-if="appMode === 'section' && currentSection === 'repos'"
        @section="openDoor($event)"
        @open="openAddlPage($event)"
      />
    </Transition>

    <!-- REFERENCES: every paper, report and data set
         the site leans on, organised by chapter or by author (?by=,
         ?chapter=). A flat layer above the globe like the Repos table. -->
    <Transition name="section-fade">
      <SectionReferences
        v-if="appMode === 'section' && currentSection === 'references'"
      />
    </Transition>

    <!-- THE TAKEAWAY BEAT: each chapter's last beat,
         and the Introduction's last step — the page dims and the takeaway
         grows into a centred card (TakeawayPop.vue; lines from
         config/takeaways.ts). Last in the DOM: above every page layer
         (Ch2Results shares its z-index 9), under the chrome. -->
    <TakeawayPop
      :show="takeawayPop !== null"
      :text="takeawayPopText.text"
      :animate="takeawayPopAnimate"
      :source="takeawayPopText.source"
      :spotlight="takeawayPopText.spotlight"
      :place="takeawayPopText.place"
      :delay-ms="takeawayPopText.delayMs"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter, type LocationQuery, type RouteLocationNormalized } from 'vue-router'
import Globe from '../components/Globe.vue'
import InsetZoom from '../components/InsetZoom.vue'
import LakeVideoPopup from '../components/LakeVideoPopup.vue'
import WaterPathButton from '../components/WaterPathButton.vue'
import SlabActionButton from '../components/SlabActionButton.vue'
import DrainLakeButton from '../components/DrainLakeButton.vue'
import DrainageLegend from '../components/DrainageLegend.vue'
import ChapterTitleCard from '../components/ChapterTitleCard.vue'
import TakeawayPop from '../components/TakeawayPop.vue'
import { CH1_TAKEAWAY, CH2_TAKEAWAY, CH3_TAKEAWAY, INTRO_TAKEAWAY } from '../config/takeaways'
import { INTRO_STEP } from '../config/introSteps'
import { ch3First } from '../config/ch3Beats'
import StressLegend from '../components/StressLegend.vue'
import BlisterStressLegend from '../components/BlisterStressLegend.vue'
import SimViewControls from '../components/SimViewControls.vue'
import SimImageryDiffLegend from '../components/SimImageryDiffLegend.vue'
import Ch2CenterLakesMap from '../components/Ch2CenterLakesMap.vue'
import Ch2FlowArrow from '../components/Ch2FlowArrow.vue'
import SimBlockCards from '../components/SimBlockCards.vue'
import DrainDomainButton from '../components/DrainDomainButton.vue'
import SimLakeCard from '../components/SimLakeCard.vue'
import PhaseSpacePanel from '../components/PhaseSpacePanel.vue'
import Ch2Results from '../components/Ch2Results.vue'
import Ch2BedLegend from '../components/Ch2BedLegend.vue'
import Ch2Teaser from '../components/Ch2Teaser.vue'
import Ch2Slab from '../components/Ch2Slab.vue'
import {
  CH2_BEAT,
  CH2_PHASE,
  ch2FigurePass,
  ch2IsBlockPhase,
  ch2IsImageryPhase,
  ch2IsResultsPhase,
  ch2IsTakeaway,
  ch2Phase,
  CH2_BED_NEIGHBOUR,
  ch2BedRange,
  ch2IsStationPhase,
  ch2SecondDefault,
} from '../config/ch2Beats'
import SimBcButton from '../components/SimBcButton.vue'
import SimBcCards from '../components/SimBcCards.vue'
import { BC_LAKES } from '../config/ch2BcData'
import { BC_KEYS, TRUE_EXAG, bcView, focusCamDir, type BcKey } from '../config/simBcGeo'
import type { SimCatalogLake, SimFace, SimField } from '../config/simLakes'
import {
  CH2_DEFAULT_LAKE,
  ch2FaceOf,
  ch2FieldOf,
  ch2ImageryDiff,
  ch2StepShown,
  ch2View,
  ch2ViewOf,
  setCh2View,
  type Ch2Layer,
  type Ch2Stage,
} from '../config/ch2State'
import TheoryPanel from '../components/TheoryPanel.vue'
import TwinGlobes from '../components/TwinGlobes.vue'
import MenuCard from '../components/MenuCard.vue'
import SectionMotivation from '../components/sections/SectionMotivation.vue'
import LiteratureTimeline from '../components/LiteratureTimeline.vue'
import FieldworkExplorer from '../components/FieldworkExplorer.vue'
import VelocityColorbar from '../components/VelocityColorbar.vue'
import { seasonUi } from '../components/seasonClock'
import type { FieldworkLayerState } from '../components/sections/SectionMotivation.vue'
import SectionCh1 from '../components/sections/SectionCh1.vue'
import { CH1_MOVIE_LAKE, ch1At, ch1First, ch1IsLakesStage, ch1IsTwinsStage } from '../config/ch1Beats'
import SectionCh2 from '../components/sections/SectionCh2.vue'
import SectionCh3, { warmCh3Openers } from '../components/sections/SectionCh3.vue'
import SectionStub from '../components/sections/SectionStub.vue'
import SectionAdditionalWork from '../components/sections/SectionAdditionalWork.vue'
import SectionTerminalBench from '../components/sections/SectionTerminalBench.vue'
import SectionFracture from '../components/sections/SectionFracture.vue'
import SectionLabelLakes from '../components/sections/SectionLabelLakes.vue'
import SectionRevisit from '../components/sections/SectionRevisit.vue'
import SectionRepos from '../components/sections/SectionRepos.vue'
import SectionReferences from '../components/sections/SectionReferences.vue'
import SectionConclusion from '../components/sections/SectionConclusion.vue'
import SectionAcknowledgements from '../components/sections/SectionAcknowledgements.vue'
import { PERSONAL_LINKS, AVATAR_URL } from '../config/person'
import SectionMgsim from '../components/sections/SectionMgsim.vue'
import type { MgsimUiState } from '../components/sections/SectionMgsim.vue'
import { mediaUrl, warmPlain } from '../config/media'
import {
  DOOR_TRAIL_KEY,
  isBeatSection,
  leaveLabel,
  parseBeatParam,
  pathNext,
  pathPrev,
  readDoorTrail,
  sameDoorPage,
  type DoorStop,
} from '../config/sitePath'
import BeatLandmarks from '../components/BeatLandmarks.vue'
import { LANDMARKS } from '../config/landmarks'
import { isDeeperChapter, type DeeperChapter } from '../config/deeperDive'
import {
  SECTIONS,
  navSections,
  primarySections,
  auxSections,
  sectionById,
  type SectionId,
} from '../config/sections'

// All media resolves through mediaUrl() against VITE_MEDIA_BASE_URL.
const usaBasemapSrc = mediaUrl('shared/usa_basemap.png')
const logoSdssSrc = mediaUrl('shared/logo_sdss.png')
const logoIcyphysicsSrc = mediaUrl('shared/logo_icyphysics.png')
const logoMineralxSrc = mediaUrl('shared/logo_mineralx.png')
const logoNsfSrc = mediaUrl('shared/logo_nsf.png')
const silhouetteUrl = mediaUrl('shared/greenland_silhouette.png')

// Section identity (labels, order, blurbs, thumbs) lives in the shared
// registry — src/config/sections.ts.

type AppMode = 'intro' | 'globe' | 'menu' | 'section'
// The menu page's object, a bit bigger (the director wanted it filling more
// of the room it has on the left side): Globe
// fits it to the room left of the menu panel and centres it there. These
// are .menu-panel's own width (48vw, max 620px) — keep the two in step.
// Menu only: every other mode keeps the plain view.
const MENU_STAGE_FIT = { rightVw: 0.48, rightMaxPx: 620 }
const appMode = ref<AppMode>('intro')
const currentSection = ref<SectionId | null>(null)
// Additional Work sub-page: null = the card
// grid, 'mgsim' = the bed-ensemble page (/additional-work/mgsim, keeps
// the globe), 'terminal-bench' = the benchmark-task page (flat, no
// globe). Declared here so syncFromRoute (called at setup, below) can
// set it.
// 'deeper' = the toggle's second stop, "Deeper dive into the chapters"
// (/additional-work/deeper/<chapter>): the same SectionAdditionalWork
// page, its other view — a side room for the shared pills like the doors
// (back → the grid, next → Repos).
// 'revisit' = "Revisiting lake drainage papers" (/additional-work/revisit,
// SectionRevisit.vue): keeps the globe and drives it, like 'mgsim'.
type AddlPage = 'mgsim' | 'terminal-bench' | 'fieldwork' | 'fracture' | 'label' | 'revisit' | 'deeper'
const ADDL_PAGES: AddlPage[] = ['mgsim', 'terminal-bench', 'fieldwork', 'fracture', 'label', 'revisit', 'deeper']
const addlPage = ref<AddlPage | null>(null)
const isMgsimPage = computed(
  () => currentSection.value === 'additional-work' && addlPage.value === 'mgsim',
)
const isTbsPage = computed(
  () => currentSection.value === 'additional-work' && addlPage.value === 'terminal-bench',
)
const isFracturePage = computed(
  () => currentSection.value === 'additional-work' && addlPage.value === 'fracture',
)
const isFieldworkPage = computed(
  () => currentSection.value === 'additional-work' && addlPage.value === 'fieldwork',
)
const isLabelPage = computed(
  () => currentSection.value === 'additional-work' && addlPage.value === 'label',
)
const isRevisitPage = computed(
  () => currentSection.value === 'additional-work' && addlPage.value === 'revisit',
)
// The revisit page's own steps for the shared pills: it reports whether it
// has one (its days, its two views), and a bump hands it the press.
const revisitNav = ref<{ next: boolean; back: boolean }>({ next: false, back: false })
const revisitAdvanceTrigger = ref(0)
const revisitBackTrigger = ref(0)
// Any Additional-Work door page (a side room of the site path).
const isAddlDoorPage = computed(
  () => currentSection.value === 'additional-work' && addlPage.value !== null,
)
// The card grid and the Terminal-Bench page are flat: they are opaque
// full-screen layers ABOVE the globe, which keeps rendering untouched
// beneath them. Do NOT hide/veil the globe for them (v-show,
// visibility, opacity — all tried): each one stalled the
// MGSIM-door landing from the grid for 30–60 s in headless Chromium
// (compositor readback of the WebGL canvas every frame).

// `baseClicks` drives the Globe's underlying scene state. Sections can
// override it (Motivation step 1 advances to 2 to show streamlines).
// Initial state: 0 = spinning hub.
const route = useRoute()
const router = useRouter()
// The deeper dive's chapter lives in the path (/additional-work/deeper/
// chapter2); the router only admits the three chapters.
const deeperChapter = computed<DeeperChapter>(() => {
  const c = route.params.chapter
  return isDeeperChapter(c) ? c : 'chapter1'
})
const baseClicks = ref(0)

// If a section emits `globe-clicks` (e.g. Motivation step 1 wants
// streamlines), override baseClicks for that section's duration.
const sectionGlobeOverride = ref<number | null>(null)
const globeClicks = computed(
  () => sectionGlobeOverride.value ?? baseClicks.value
)

// 3D length-scale arrows visibility — toggled by sections (Motivation
// step 0 turns them on).
const showArrows = ref(false)

// DEM rollback progress (0–1). Driven by SectionMotivation's step-0
// auto-ramp. Drives Globe's uRollback uniforms + the cross-section
// slab opacity. Resets to 0 when leaving Motivation.
const rollbackProgress = ref(0)

// Chapter-driven camera focus. Set by SectionCh1 (and any other future
// chapter section that wants to fly the camera to a specific feature).
// Cleared to null when the section unmounts so phase-controlled camera
// resumes.
const chapterFocus = ref<{
  lat: number
  lon: number
  cameraLat?: number
  cameraLon?: number
  distance?: number
  fovDeg?: number
  durationMs?: number
  focalElevM?: number
  focalOnSurface?: boolean
  focalExag?: number
  fit?: {
    fracTLon: number
    halfKm: number
    rect: { x: number; y: number; w: number; h: number }
  }
  upNorth?: boolean
  up?: [number, number, number]
} | null>(null)
function onChapterFocus(target: typeof chapterFocus.value): void {
  // A section re-framing (lake change, beat jump, back to the lakes)
  // ends boundary-condition mode: its saved framing is stale now.
  if (target !== null && ch2BcOn.value) dropBcMode()
  // A null here during a chapter→chapter handoff comes from
  // the OLD section's unmount cleanup — the new chapter emits its own
  // framing in the same tick. Passing the null through started Globe's
  // return-to-menu lerp mid-handoff (the "zooms out and back in").
  if (
    target === null &&
    (currentSection.value === 'chapter1' ||
      currentSection.value === 'chapter2' ||
      currentSection.value === 'chapter3' ||
      isMgsimPage.value ||
      isRevisitPage.value)
  ) {
    return
  }
  chapterFocus.value = target
  if (target !== null) releaseStageFitHold()
}

// Menu → a section whose opening flies the camera: the Globe holds the
// menu's stage fit until that flight starts, which then carries it out
// (without the hold, the object shrank on its own clock, then flew). A
// safety timeout lets it ease out alone if no flight comes.
const STAGE_FIT_HOLD_SECTIONS: readonly string[] = ['introduction', 'chapter1', 'chapter2', 'chapter3']
const stageFitHold = ref(false)
let stageFitHoldTimer: number | null = null
function releaseStageFitHold(): void {
  if (stageFitHoldTimer !== null) {
    window.clearTimeout(stageFitHoldTimer)
    stageFitHoldTimer = null
  }
  stageFitHold.value = false
}
function holdStageFit(): void {
  releaseStageFitHold()
  stageFitHold.value = true
  stageFitHoldTimer = window.setTimeout(releaseStageFitHold, 2500)
}

const lakeOverlay = ref<{ lat: number; lon: number; radiusKm?: number; color?: string; opacity?: number } | null>(null)
function onLakeOverlay(target: typeof lakeOverlay.value): void {
  lakeOverlay.value = target
}

// Unified south-to-NL knife reveal. Sections emit a single
// chapter-reveal carrying the cut latitude + slab opacity + idealize
// morph; Globe.vue fans it out internally to the basemap shader's
// uChapterCutSinLat and the slab material's uniforms. Single prop ⇒
// no risk of the cut latitude and slab latitude drifting out of sync
// (was its own bug class before this unification).
const chapterReveal = ref<{
  latDeg: number
  slabOpacity?: number
  idealize?: number
  cutBasemap?: boolean
} | null>(null)
function onChapterReveal(target: typeof chapterReveal.value): void {
  chapterReveal.value = target
}

// JOG-chapter additions (the 5-beat sequence introduced in Ch.1: pan →
// flash CW lake polygons → flash North Lake → velocity + streamline →
// streamline cross-section reveal). Each emit from SectionCh1 becomes a
// reactive prop on Globe.
const lakePolygons = ref<{
  dataUrl: string
  opacity?: number
  baseColor?: string
  baseAlpha?: number
  highlightId?: string | null
  highlightFillColor?: string
  highlightOutlineColor?: string
  highlightScale?: number
  highlightGlow?: boolean
  featured?: boolean
  inert?: boolean
  keep?: { id: string; opacity: number } | null
} | null>(null)
function onLakePolygons(target: typeof lakePolygons.value): void {
  lakePolygons.value = target
}
// Ch.1 beats 1–2: North Lake on the surface behind the cross-section face.
const lakeCutaway = ref<{
  dataUrl: string
  id: string
  cutLatDeg: number
  color: string
  opacity: number
  water: number
} | null>(null)

// The five featured drainage-class lakes (ESSD fig-4). Mirrors
// cinematic/scene_ch01/build_featured_lakes.py's FEATURED list —
// id → popup registry. Media lives at R2 ch01/lakes/<id>.{mp4,json}.
const FEATURED_LAKES: Record<string, { name: string; season: string }> = {
  CW2019_1889: { name: 'North Lake', season: '15 May → 30 June 2019' },
  CW2019_1848: { name: 'Lake 1848', season: '1 May → 30 June 2019' },
  CW2019_1907: { name: 'Lake 1907', season: '1 May → 15 June 2019' },
  CW2019_2330: { name: 'Lake 2330', season: '15 May → 15 Aug 2019' },
  CW2019_1597: { name: 'Lake 1597', season: '1 July → 30 Sep 2019' },
}

// The seven PNAS center lakes (Ch.2; all hydrofracture drainages).
// Mirrors cinematic/scene_ch02/build_pnas_lakes.py — media at R2
// ch02/lakes_valid/<id>.{mp4,json} (the black-frame ch02/lakes/ set is retired).
const CH2_LAKES: Record<string, { name: string; season: string }> = {
  CW2019_1910: { name: 'Lake 1910', season: '25 June → 10 Aug 2019' },
  CW2019_1951: { name: 'Lake 1951', season: '5 June → 25 July 2019' },
  CW2019_2394: { name: 'Lake 2394', season: '15 May → 5 July 2019' },
  CW2019_2411: { name: 'Lake 2411', season: '1 July → 20 Aug 2019' },
  CW2019_2416: { name: 'Lake 2416', season: '20 July → 5 Sep 2019' },
  CW2019_2511: { name: 'Lake 2511', season: '20 July → 5 Sep 2019' },
  CW2019_2520: { name: 'Lake 2520', season: '5 June → 25 July 2019' },
}

// Lake-video popup state. Set by onLakeBeaconClick; the
// LakeVideoPopup component renders when non-null and clears itself
// via the @close emit. sidecarUrl is the per-frame metadata
// (date + p_water + class accent + ticks) driving the popup's date
// badge + normalized-volume chart.
const lakeVideo = ref<{
  id: string
  src: string
  sidecarUrl: string
  title: string
} | null>(null)

// Chapter beat counters — the headless sections watch these props and
// step on change. Counters (not booleans) so equal-value edges are
// no-ops; one bump = one step. Advance is bumped by the top-right
// "next" pill, the in-canvas buttons, and "Where does the water go?";
// back by the top-right "back" pill.
const ch1AdvanceTrigger = ref(0)
const ch1RevealTrigger = ref(0)
const ch1BackTrigger = ref(0)
const ch2AdvanceTrigger = ref(0)
const ch2BackTrigger = ref(0)
const ch3AdvanceTrigger = ref(0)
const ch3BackTrigger = ref(0)
const introAdvanceTrigger = ref(0)
const introBackTrigger = ref(0)

// Last-beat flags from the beat-change emits — flip the next pill's
// label to the next chapter's name.
const ch1IsLastBeat = ref(false)
const ch2IsLastBeat = ref(false)
const ch3IsLastBeat = ref(false)
const introIsLastBeat = ref(false)
const introBeat = ref(0)
// The Acknowledgements' split-out steps (ACK_STEPS).
const ackAdvanceTrigger = ref(0)
const ackBackTrigger = ref(0)
const ackBeat = ref(0)
const ackIsLastBeat = ref(false)
function onAckBeatChange(beat: number, isLast: boolean): void {
  beatReportedFor.value = 'acknowledgements'
  ackBeat.value = beat
  ackIsLastBeat.value = isLast
}
// The Conclusion's takeaway steps (rest, then each chapter's
// takeaway pops out in turn).
const concAdvanceTrigger = ref(0)
const concBackTrigger = ref(0)
const concBeat = ref(0)
const concIsLastBeat = ref(false)
function onConcBeatChange(beat: number, isLast: boolean): void {
  beatReportedFor.value = 'conclusion'
  concBeat.value = beat
  concIsLastBeat.value = isLast
}
// Which beat page has reported its beat since it mounted (its first
// beat-change can lag a deep link — Ch.2 waits for its lake metadata).
// Until it has, the pills defer to the page instead of trusting a stale
// beat number (a `back` then would skip the whole page).
const beatReportedFor = ref<SectionId | null>(null)
function onIntroBeatChange(beat: number, isLast: boolean): void {
  beatReportedFor.value = 'introduction'
  introBeat.value = beat
  introIsLastBeat.value = isLast
}

// Which beat page owns the pills' in-page steps right now (null = a flat
// page: its pills only ever leave it). The Additional-Work door pages
// (MGSIM included) are flat for the path.
const beatChapter = computed<'introduction' | 'chapter1' | 'chapter2' | 'chapter3' | 'conclusion' | 'acknowledgements' | null>(() => {
  const id = currentSection.value
  return id && isBeatSection(id) ? (id as 'introduction' | 'chapter1' | 'chapter2' | 'chapter3' | 'conclusion' | 'acknowledgements') : null
})
const activeBeat = computed(() => {
  switch (beatChapter.value) {
    case 'introduction': return introBeat.value
    case 'chapter1': return ch1Beat.value
    case 'chapter2': return ch2Beat.value
    case 'chapter3': return ch3Beat.value
    case 'conclusion': return concBeat.value
    case 'acknowledgements': return ackBeat.value
    default: return 0
  }
})
// The chapter title card (ChapterTitleCard.vue): up on a chapter's
// LANDING — its first beat, once the section has reported it (so BACK
// onto a last beat or a `?beat=N` link never flashes it) — and down on
// the first NEXT. Chapter 2's first NEXT opens a lake's popup without
// leaving beat 0, and a visitor can open one on Chapter 1's lakes too:
// an open popup drops the card as well. `chapterCardText` keeps the
// words through the fade-out, when the section may already have changed.
// The card hangs top-left, except on Chapter 3's landing, whose lake
// callouts hold that corner — there it takes the top-right, which that
// page leaves free (Chapter 1's has the drainage legend there).
type ChapterCardText = { label: string; title: string; side: 'left' | 'right'; status: string; venue: string }
const chapterCard = computed<ChapterCardText | null>(() => {
  const s = sectionById(currentSection.value)
  return s?.title
    ? { label: s.label, title: s.title, side: s.id === 'chapter3' ? 'right' : 'left', status: s.status ?? '', venue: s.venue ?? '' }
    : null
})
const showChapterCard = computed(
  () =>
    appMode.value === 'section' &&
    chapterCard.value !== null &&
    beatReportedFor.value === currentSection.value &&
    activeBeat.value === 0 &&
    lakeVideo.value === null,
)
const chapterCardText = ref<ChapterCardText>({ label: '', title: '', side: 'left', status: '', venue: '' })
watch(chapterCard, (c) => { if (c) chapterCardText.value = c }, { immediate: true })
// Where the path is, for measuring tools (a performance-walk script can
// read it to label every press): the beat page and its reported beat, like
// the Globe's `__texturesPending`. Not read by the site.
watch(
  [currentSection, activeBeat, beatReportedFor, () => appMode.value],
  ([sec, beat, reported, mode]) => {
    ;(window as any).__pathBeat = { mode, section: sec, beat, reported: reported === sec }
  },
  { immediate: true },
)
const activeIsLastBeat = computed(() => {
  switch (beatChapter.value) {
    case 'introduction': return introIsLastBeat.value
    case 'chapter1': return ch1IsLastBeat.value
    case 'chapter2': return ch2IsLastBeat.value
    case 'chapter3': return ch3IsLastBeat.value
    case 'conclusion': return concIsLastBeat.value
    case 'acknowledgements': return ackIsLastBeat.value
    default: return true
  }
})
// The shared pills' labels (config/sitePath.ts): "next"/"back" inside
// the path, a chapter's short name when next leaves for it, "menu" at the
// two ends. The 6.4rem footprint never changes.
const navNextLabel = computed(() =>
  beatChapter.value && !activeIsLastBeat.value ? 'next' : leaveLabel(pathNext(currentSection.value)),
)
const navBackLabel = computed(() =>
  !doorBackTarget() && !isAddlDoorPage.value && activeBeat.value === 0 && pathPrev(currentSection.value) === null
    ? 'menu'
    : 'back',
)

// The sub-menu (BeatLandmarks under the ribbon, config/landmarks.ts):
// only inside a beat page. Its marker follows the page's reported beat;
// before the page has reported (Ch.2 waits for its lake metadata) it
// trusts the URL's `?beat=`, the beat the page is about to land on.
const landmarkData = computed(() => (beatChapter.value ? LANDMARKS[beatChapter.value] ?? null : null))
const landmarkBeat = computed(() => {
  const sec = beatChapter.value
  const d = landmarkData.value
  if (!sec || !d) return 0
  return beatReportedFor.value === sec ? activeBeat.value : parseBeatParam(route.query.beat, d.count)
})
// A notch click. The page lands on the beat exactly as a `?beat=N` deep
// link lands it (each page's jumpTo watcher runs its mount path), and the
// URL carries the beat so a reload lands there too. Ch.2's in-beat flags
// (`drained`, `model`) would override `beat` on a reload, so they go.
const BEAT_FLAG_KEYS = ['drained', 'model', 'stage', 'layer', 'field'] as const
const beatJump = ref<{ section: SectionId; beat: number; seq: number } | null>(null)
let beatJumpSeq = 0
function jumpToBeat(beat: number): void {
  const sec = beatChapter.value
  if (!sec) return
  const query: LocationQuery = { ...route.query, beat: String(beat) }
  for (const k of BEAT_FLAG_KEYS) delete query[k]
  router.replace({ query })
  beatJumpSeq += 1
  beatJump.value = { section: sec, beat, seq: beatJumpSeq }
}

// One-shot TheoryPanel entry effect (beat 3→4 seam morph).
const theoryEntryFx = ref<'seam' | null>(null)
function onTheoryEntryFx(v: 'seam' | null): void {
  theoryEntryFx.value = v
}

// Drainage-legend hover → that lake pulses slowly on the globe.
const featuredPulseId = ref<string | null>(null)
// Pointer over a featured lake on the globe (Globe's lake-beacon-hover):
// Ch.3 beat 0 lights that lake's callout panel.
const featuredHoverId = ref<string | null>(null)
// A featured lake CLICKED on the globe while Ch.3 is up — beat 0 pins
// the panel instead of opening Ch.1's popup. seq bumps per click.
const ch3LakeClick = ref<{ id: string; seq: number } | null>(null)
// Ch.3 beat 1: the labeled population, drawn by SectionCh3 into a canvas
// the Globe drapes over the central-west strip.
const lakeStrip = ref<{
  canvas: HTMLCanvasElement
  lonW: number
  lonE: number
  latS: number
  latN: number
  opacity: number
  version: number
} | null>(null)

// Drainage-class legend rides Beat 0's featured-lakes overlay.
const showDrainageLegend = computed(
  () =>
    currentSection.value === 'chapter1' &&
    ch1IsLakesStage(ch1Beat.value) &&
    // the large movie card covers the legend's corner — one or the other
    lakeVideo.value === null &&
    !!lakePolygons.value?.featured,
)

// "Where does the water go?" appears while the NORTH LAKE video is
// open — that's the popup that launches the hydrofracture story. The
// other four lakes' popups are exploration; they just close.
const showWaterPathButton = computed(
  () => lakeVideo.value !== null && lakeVideo.value.id === 'CW2019_1889',
)

// Ch.1 beat gate for the anchored slab action buttons.
function ch1BeatIs(b: number): boolean {
  return currentSection.value === 'chapter1' && ch1Beat.value === b
}

function bumpCh1Advance(): void {
  ch1AdvanceTrigger.value += 1
}
function bumpBeatAdvance(): void {
  if (beatChapter.value === 'introduction') introAdvanceTrigger.value += 1
  else if (beatChapter.value === 'acknowledgements') ackAdvanceTrigger.value += 1
  else if (beatChapter.value === 'conclusion') concAdvanceTrigger.value += 1
  else if (beatChapter.value === 'chapter3') ch3AdvanceTrigger.value += 1
  else if (beatChapter.value === 'chapter2') ch2AdvanceTrigger.value += 1
  else ch1AdvanceTrigger.value += 1
}
function bumpBeatBack(): void {
  if (beatChapter.value === 'introduction') introBackTrigger.value += 1
  else if (beatChapter.value === 'acknowledgements') ackBackTrigger.value += 1
  else if (beatChapter.value === 'conclusion') concBackTrigger.value += 1
  else if (beatChapter.value === 'chapter3') ch3BackTrigger.value += 1
  else if (beatChapter.value === 'chapter2') ch2BackTrigger.value += 1
  else ch1BackTrigger.value += 1
}
// The shared pills. NEXT on a beat page always goes through the page (its
// last beat emits `advance`, which may choreograph a hand-off — Ch.1's
// twins close-out); on a flat page it takes the path straight away.
function navNext(): void {
  // The revisit page's days come first (the paper's maps, then every lake).
  if (isRevisitPage.value && revisitNav.value.next) revisitAdvanceTrigger.value += 1
  else if (beatChapter.value) bumpBeatAdvance()
  else advanceSection()
}
// BACK steps a beat page back one beat; at its first beat (or on a flat
// page) it takes the path back — onto the previous page's LAST beat, so
// the path retraces exactly. Door pages return to the Additional-Work
// grid; the Introduction's first step returns to the menu.
function navBack(): void {
  // Ch.2's lakes beat: BACK retraces NEXT — an open popup closes first.
  if (beatChapter.value === 'chapter2' && ch2PhaseNow.value === CH2_PHASE.lakes && lakeVideo.value) {
    lakeVideo.value = null
    return
  }
  // The revisit page retraces its own steps first (player → grid → the
  // cascade → its earlier days); on its first day BACK is the usual one.
  if (isRevisitPage.value && revisitNav.value.back) {
    revisitBackTrigger.value += 1
    return
  }
  // Reached through a door (config/sitePath.ts, the door trail): back to
  // exactly where it was used — before any in-page or path step.
  const door = doorBackTarget()
  if (door) {
    returnThroughDoor(door)
    return
  }
  if (beatChapter.value && (activeBeat.value > 0 || beatReportedFor.value !== beatChapter.value)) {
    bumpBeatBack()
    return
  }
  if (isAddlDoorPage.value) {
    selectSection('additional-work')
    return
  }
  const prev = pathPrev(currentSection.value)
  if (prev === null) {
    returnToMenu()
    return
  }
  navIntent = 'path'
  settleIntent(router.push(isBeatSection(prev) ? { name: prev, query: { beat: 'last' } } : { name: prev }))
}

// ── The door trail (config/sitePath.ts) ──
// Every navigation is classified here, so no door component has to know:
//   'path'  — the pills, the ribbon, the menu: the trail is cleared;
//   'exit'  — a door page's own exit pill ("← doors", "← PNAS chapter"):
//             pops the trail when it leads where the trail's top was, else
//             clears it;
//   'return'— BACK through a door: the trail minus its top;
//   none    — a door (router-link or push from a page): the trail gains
//             where it was used from, with the beat that was on screen.
// Replaces (the sub-menu's `?beat=`, References' `?by=`) and browser
// back/forward keep the entry's own trail from history.state; a tab inside
// one page (the deeper dive's chapter tabs, the grid ⇄ deeper toggle)
// carries it over.
type NavIntent = 'path' | 'exit' | 'return'
let navIntent: NavIntent | null = null
let returnTrail: DoorStop[] | null = null
let poppedNav = false
const doorTrail = ref<DoorStop[]>(readDoorTrail(window.history.state) ?? [])
let pendingNav: { intent: NavIntent | 'pop' | null; origin: Omit<DoorStop, 'landed'> | null; trail: DoorStop[] | null } | null = null

function onPopState(): void {
  poppedNav = true
}
window.addEventListener('popstate', onPopState)

/** Where a door is being used from: the route, with a beat page's beat on screen. */
function doorOrigin(from: RouteLocationNormalized): Omit<DoorStop, 'landed'> | null {
  if (typeof from.name !== 'string' || from.matched.length === 0) return null
  const query = { ...from.query } as DoorStop['query']
  const sec = from.name as SectionId
  if (isBeatSection(sec) && sec === beatChapter.value && beatReportedFor.value === sec) {
    query.beat = String(activeBeat.value)
    for (const k of BEAT_FLAG_KEYS) delete query[k]
  }
  return { name: from.name, params: { ...from.params }, query, hash: from.hash }
}

const offDoorBefore = router.beforeEach((_to, from) => {
  pendingNav = { intent: poppedNav ? 'pop' : navIntent, origin: doorOrigin(from), trail: returnTrail }
  poppedNav = false
  navIntent = null
  returnTrail = null
})
const offDoorAfter = router.afterEach((to, from, failure) => {
  if (failure) return
  const p = pendingNav
  pendingNav = null
  const stored = readDoorTrail(window.history.state)
  const cur = doorTrail.value
  const toName = typeof to.name === 'string' ? to.name : ''
  const fromName = typeof from.name === 'string' ? from.name : ''
  let trail: DoorStop[]
  if (!p) trail = stored ?? []
  else if (p.intent === 'return') trail = p.trail ?? cur.slice(0, -1)
  else if (p.intent === 'pop') trail = stored ?? []
  else if (p.intent === 'path') trail = []
  else if (stored) trail = stored // a replace keeps its entry's trail
  else if (sameDoorPage(fromName, toName)) trail = cur
  else if (cur.length && sameDoorPage(cur[cur.length - 1].name, toName)) trail = cur.slice(0, -1)
  else if (p.intent === 'exit' || !p.origin) trail = []
  else trail = [...cur, { ...p.origin, landed: typeof to.query.beat === 'string' ? to.query.beat : null }]
  doorTrail.value = trail
  try {
    window.history.replaceState({ ...window.history.state, [DOOR_TRAIL_KEY]: JSON.parse(JSON.stringify(trail)) }, '')
  } catch {
    /* the trail stays in memory */
  }
})
// A push that never starts (a duplicate) must not leave its intent behind.
function settleIntent(p: Promise<unknown>): void {
  void p.finally(() => {
    navIntent = null
    returnTrail = null
  })
}
onBeforeUnmount(() => {
  offDoorBefore()
  offDoorAfter()
  window.removeEventListener('popstate', onPopState)
})

/** The stop BACK returns to, or null when BACK keeps its usual meaning.
 *  On a beat page a door led into, only on the beat it landed on. */
function doorBackTarget(): DoorStop | null {
  const t = doorTrail.value
  const top = t.length ? t[t.length - 1] : null
  if (!top) return null
  const sec = beatChapter.value
  if (sec) {
    if (beatReportedFor.value !== sec) return null
    const landed = parseInt(top.landed ?? '0', 10)
    if (activeBeat.value !== (Number.isFinite(landed) ? landed : 0)) return null
  }
  return top
}
function returnThroughDoor(stop: DoorStop): void {
  // The bed-ensemble page opened from Chapter 2 goes back through its own
  // block-preserving hand-off (the same as its "← PNAS chapter" pill).
  if (isMgsimPage.value && stop.name === 'chapter2' && route.query.from === 'ch2') {
    onMgsimExit('ch2')
    return
  }
  navIntent = 'return'
  returnTrail = doorTrail.value.slice(0, -1)
  settleIntent(router.push({ name: stop.name, params: stop.params, query: stop.query, hash: stop.hash }))
}
/** A door that is a whole page (Repos' pills, Terminal-Bench's chapter link). */
function openDoor(id: SectionId): void {
  router.push({ name: id })
}
/** A door page's own exit pill. */
function exitTo(id: SectionId): void {
  navIntent = 'exit'
  settleIntent(router.push({ name: id }))
}

// The presenter remote (the director presents with a Logi Spotlight 2 and
// wanted its next button to mean exactly what clicking NEXT means).
// A Logi Spotlight is a keyboard to the
// browser: its next/back buttons arrive as Page Down / Page Up (the
// plug-and-play default) or Right / Left arrow (the Logi Options+
// "Keystroke" mapping, and what Keynote-style apps expect). All four
// route into the SAME navNext/navBack the pills call, so the remote walks
// the deterministic path exactly as a click would — and so does the
// keyboard's arrow keys, which is how to test it without the remote.
//   · landing: NEXT = the click on Greenland (begins the tour);
//     menu: NEXT = the first page of the path, BACK does nothing;
//     the globe's settling spin ignores both.
//   · a text field keeps its keys (← → move the caret in an input), as
//     does any overlay that already owns the arrows
//     (the deeper-dive lightbox and the Ch.2 field viewer stop the
//     event in the capture phase, so it never reaches here).
//   · a slider the MOUSE focused (a dragged ACL slider keeps focus) or a
//     video element does NOT keep them — a remote press is navigation
//     intent; preventDefault stops the slider nudge / 5 s seek / page
//     scroll. A slider the KEYBOARD focused (Tab) does keep ← →. The
//     tell is the last pointerdown target (`pointerEl`): the slider
//     itself = the mouse put the focus there. (`:focus-visible` cannot
//     tell — Chromium flips it to true before the keydown is dispatched.)
//   · auto-repeat from a held key is ignored; modifier chords (⌘←
//     history back) are left to the browser.
function onPresenterKey(e: KeyboardEvent): void {
  if (e.defaultPrevented || e.repeat || e.metaKey || e.ctrlKey || e.altKey) return
  const dir =
    e.key === 'ArrowRight' || e.key === 'PageDown' ? 1
    : e.key === 'ArrowLeft' || e.key === 'PageUp' ? -1
    : 0
  if (dir === 0) return
  const t = e.target as HTMLElement | null
  if (t) {
    const tag = t.tagName
    const type = (t as HTMLInputElement).type
    if (tag === 'TEXTAREA' || tag === 'SELECT' || t.isContentEditable) return
    if (tag === 'INPUT' && type !== 'range' && type !== 'checkbox' && type !== 'radio' && type !== 'button' && type !== 'submit') return
    if (tag === 'INPUT' && type === 'range' && e.key.startsWith('Arrow') && t !== pointerEl) return
  }
  switch (appMode.value) {
    case 'intro':
      if (dir === 1) beginTour()
      break
    case 'menu':
      if (dir === 1) selectSection(navSections[0].id)
      break
    case 'section':
      if (dir === 1) navNext()
      else navBack()
      break
    default:
      return
  }
  e.preventDefault()
}
let pointerEl: EventTarget | null = null
function onPointerDown(e: PointerEvent): void {
  pointerEl = e.target
}
window.addEventListener('pointerdown', onPointerDown, true)
window.addEventListener('keydown', onPresenterKey)
onBeforeUnmount(() => {
  window.removeEventListener('pointerdown', onPointerDown, true)
  window.removeEventListener('keydown', onPresenterKey)
})

// Twin ACL + max-stress 3D globes (Ch.1's closing beat; the α/h maps
// beat precedes it — config/ch1Beats.ts).
// The takeaway beat after it keeps them up, dimmed (TakeawayPop).
const showTwinGlobes = computed(
  () => currentSection.value === 'chapter1' && ch1IsTwinsStage(ch1Beat.value),
)


// ── Ch.1 → Ch.2 handoff: instead of a hard route cut, the
// twins CLOSE — right pane collapses, ACL paint dissolves, the left
// greenland object glides into Chapter 2's opening framing — while the
// main globe underneath is sent to the SAME framing; then we route and
// crossfade the twins canvas away. ──
const ch1TwinsClosing = ref(false)
const twinsLinger = ref(false)
function onCh1AdvanceRequest(): void {
  // SectionCh1 asks to leave from its last beat (the takeaway, over the
  // twins) — the twins close into Chapter 2 from there.
  if (currentSection.value === 'chapter1' && ch1IsTwinsStage(ch1Beat.value)) {
    if (ch1TwinsClosing.value) return
    ch1TwinsClosing.value = true
    // Aim the (paused) main globe at Chapter 2's opening framing — it
    // snaps there on unpause, exactly under the twins' final frame.
    chapterFocus.value = {
      lat: 70.1,
      lon: -49.3,
      cameraLat: 61.6,
      cameraLon: -67.2,
      distance: 0.6,
      fovDeg: 13,
      durationMs: 400,
    }
    return
  }
  advanceSection()
}
function onTwinsClosed(): void {
  twinsLinger.value = true
  ch1TwinsClosing.value = false
  advanceSection()
  window.setTimeout(() => {
    twinsLinger.value = false
  }, 700)
}

function onLakeBeaconClick(lakeId: string): void {
  if (currentSection.value === 'chapter3') {
    ch3LakeClick.value = { id: lakeId, seq: (ch3LakeClick.value?.seq ?? 0) + 1 }
    return
  }
  const isCh2 = currentSection.value === 'chapter2'
  const lake = isCh2 ? CH2_LAKES[lakeId] : FEATURED_LAKES[lakeId]
  if (!lake) return
  // Ch.1's and Ch.2's popups play the VALID-frame movies (only the days Sentinel-2
  // imaged — no blank days); the clicked lake becomes the
  // chapter's lake (NEXT zooms in on it).
  // (Ch.1's set: ch01/lakes_valid/,
  // cinematic/scene_ch01/build_featured_lakes_valid.py.)
  const dir = isCh2 ? 'ch02/lakes_valid' : 'ch01/lakes_valid'
  if (isCh2) setCh2Lake(lakeId)
  lakeVideo.value = {
    id:         lakeId,
    src:        mediaUrl(`${dir}/${lakeId}.mp4`),
    sidecarUrl: mediaUrl(`${dir}/${lakeId}.json`),
    title:      lake.name,
  }
}

function advanceToCrossSection(): void {
  // Click on the in-canvas water-path button: close the video dock AND
  // take Chapter 1 to the cross-section reveal in one user action —
  // from any lakes-stage step (the HF movie step's NEXT is the same move).
  lakeVideo.value = null
  ch1RevealTrigger.value += 1
}

// Chapter 1's lakes stage: NEXT from the lakes
// opens the no-drainage lake's movie, NEXT swaps to North Lake's (HF),
// NEXT flies to the cross-section; BACK walks the same steps. The popup
// is the beat's content, so the beat opens it; a hand-clicked lake on
// any of the three steps still opens that lake's.
function openCh1MovieFor(beat: number): void {
  const seg = ch1At(beat)?.id
  const id = seg ? CH1_MOVIE_LAKE[seg] : undefined
  if (id && lakeVideo.value?.id !== id) onLakeBeaconClick(id)
}
let ch1PrevBeat = -1
function onCh1BeatChange(beat: number, isLast: boolean): void {
  const from = ch1PrevBeat
  ch1PrevBeat = beat
  beatReportedFor.value = 'chapter1'
  ch1Beat.value = beat
  ch1IsLastBeat.value = isLast
  if (ch1IsLakesStage(beat)) {
    // The two movies NEXT opens (ND, then North Lake), warmed as the
    // lakes land — cold, the first frame took ~0.8 s after the press.
    for (const id of Object.values(CH1_MOVIE_LAKE)) warmPlain(mediaUrl(`ch01/lakes_valid/${id}.mp4`))
    openCh1MovieFor(beat)
    // BACK from the ND movie onto the bare lakes: the popup closes.
    if (beat === ch1First('lakes') && from > beat && lakeVideo.value !== null) lakeVideo.value = null
    return
  }
  // Leaving the lakes stage (either direction) dismisses the video so
  // the cross-section reveal isn't crowded by an open dock.
  if (lakeVideo.value !== null) lakeVideo.value = null
  featuredPulseId.value = null
}

// ── Ch.2 wiring ──
const ch2Beat = ref(0)
const ch2PhaseNow = computed(() => ch2Phase(ch2Beat.value))
/** The FIRST center lake (2394 unless the visitor clicked another). */
const ch2SelectedLake = ref(CH2_DEFAULT_LAKE)
/** A lake clicked on `lakes/2` (null = the default second lake). */
const ch2SecondPick = ref<string | null>(null)
/** The SECOND center lake (config/ch2Beats.ts `lakes/2` …): Lake 1951 —
 *  the bed-topography case — or 2394 when 1951 went first. */
const ch2SecondLake = computed(
  () => ch2SecondPick.value ?? ch2SecondDefault(ch2SelectedLake.value, CH2_DEFAULT_LAKE),
)
/** The lake the current beat's figures are about. */
const ch2ActiveLake = computed(() =>
  ch2FigurePass(ch2Beat.value) === 1 ? ch2SecondLake.value : ch2SelectedLake.value,
)
/** A lake pick (a popup click, "Zoom in") lands on the pass it was made
 *  in; a new first lake re-derives the second. */
function setCh2Lake(id: string): void {
  if (ch2FigurePass(ch2Beat.value) === 1) {
    ch2SecondPick.value = id
  } else {
    ch2SelectedLake.value = id
    ch2SecondPick.value = null
  }
}
// (The walk's stress spaces show ONLY the center lake's
// symbols — the other lakes' points come with the population page.)
/** The bed beat lights the neighbour the bed decides (config/ch2Beats.ts). */
// The key's bar is a CSS background — a plain (no-cors) request, made the
// moment Chapter 2 mounts. The Globe loads the SAME PNG as a WebGL texture
// (CORS) on the bed beat. R2 answers a no-Origin request without ACAO or
// `Vary`, so the plain entry was served to the CORS load and refused — the
// live bed beat showed a GREY bed. A marker keeps the
// two cache entries apart (the `cors=1` pattern); R2 ignores the query.
const CH2_BED_PALETTE_URL = (() => {
  const u = mediaUrl('addl/mgsim/bed_palette.png')
  return u + (u.includes('?') ? '&' : '?') + 'plain=1'
})()
const ch2BedRangeNow = computed(() => ch2BedRange(ch2ActiveLake.value))
const ch2BedLit = computed(() =>
  currentSection.value === 'chapter2' &&
  (ch2PhaseNow.value === CH2_PHASE.bed || ch2PhaseNow.value === CH2_PHASE.teaser)
    ? (CH2_BED_NEIGHBOUR[ch2ActiveLake.value] ?? null)
    : null,
)
// The block view (config/ch2State.ts): stage × layer, the director's two tiers.
// Face/field are its projection onto the payload's older words (the
// Globe, legend, phase panel and MGSIM handoff speak those).
const ch2Face = computed<SimFace>(() => ch2FaceOf(ch2View))
const ch2Field = computed<SimField>(() => ch2FieldOf(ch2View))
const ch2ImgDiff = computed(() => ch2ImageryDiff(ch2View))
// The tiers ride the block on the imagery beats (pre · post), free to
// explore; NEXT walks the path whatever was picked. On the results beats
// they stay up as the beat's headings (inert).
const ch2ControlsOn = computed(
  () =>
    currentSection.value === 'chapter2' &&
    (ch2IsImageryPhase(ch2PhaseNow.value) || ch2IsResultsPhase(ch2PhaseNow.value)),
)
function onCh2Pick(stage: Ch2Stage, layer: Ch2Layer | null): void {
  setCh2View(stage, layer)
}
/** A centre lake clicked in the inset (the director wanted every centre
 *  lake in the mini map clickable, to see this same sequence for any of
 *  them): it becomes the CURRENT pass's
 *  lake — SectionCh2 hops to it on the same beat and station. */
function onCh2InsetPick(id: string): void {
  if (currentSection.value !== 'chapter2' || !ch2IsBlockPhase(ch2PhaseNow.value) || ch2BcOn.value) return
  if (id === ch2ActiveLake.value) return
  setCh2Lake(id)
}
/** The idealized slab owns the screen (Ch2Slab.vue): the globe pauses. */
const ch2SlabCover = ref(false)
watch(currentSection, (s) => { if (s !== 'chapter2') ch2SlabCover.value = false })
/** The depth average has landed: `slab-da` is a transit beat — on to the
 *  three panels as if NEXT were pressed (config/ch2Beats.ts). */
function onSlabTransitDone(): void {
  if (currentSection.value === 'chapter2' && ch2Beat.value === CH2_BEAT['slab-da']) ch2AdvanceTrigger.value += 1
}
/** The teaser beat's cycle position (SectionCh2 `teaser`). */
const ch2Teaser = ref<{ frame: number; n: number; label: string } | null>(null)
const ch2Dates = ref<{ pre: string; post: string } | null>(null)
// Boundary-condition mode.
const ch2BcOn = ref(false)
/** The clicked boundary card (null = the BC overview). */
const ch2BcFocus = ref<BcKey | null>(null)
/** The card under the pointer (its boundary lights up on the block). */
const ch2BcHover = ref<BcKey | null>(null)
const ch2FaceModel = computed<'elastic' | 'viscous'>(() =>
  ch2Face.value === 'elastic' ? 'elastic' : 'viscous',
)
const ch2SimBc = computed(() => ({
  // the block's own beats only — the results walk paints it, no BCs
  on: ch2BcOn.value && currentSection.value === 'chapter2' && ch2IsImageryPhase(ch2PhaseNow.value),
  model: ch2FaceModel.value,
  focus: ch2BcFocus.value,
  lakeId: ch2ActiveLake.value,
  hover: ch2BcHover.value,
}))

// ── BC mode camera (chapterFocus — the Globe's one camera system) ──
// Entering saves the landed framing + exaggeration; the overview steps
// back to the whole model domain, a card flies head-on to its boundary
// (wall views lift the exaggeration so the profile reads), and leaving
// restores exactly what the chapter had.
const BC_FOV = 2.0
/** Head-on wall views: vertical exaggeration (× true scale). */
const BC_WALL_EXAG = 5 * TRUE_EXAG
let bcSaved: { focus: NonNullable<typeof chapterFocus.value>; exag: number | null } | null = null
/** Ice opacity in BC mode (the bed view looks down through it). */
const bcSurfA = ref(1)
let bcSurfRaf = 0
function lerpBcSurfA(to: number): void {
  cancelAnimationFrame(bcSurfRaf)
  const from = bcSurfA.value
  const t0 = performance.now()
  const step = (now: number) => {
    const t = Math.min(1, (now - t0) / 900)
    const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
    bcSurfA.value = from + (to - from) * e
    if (t < 1) bcSurfRaf = requestAnimationFrame(step)
  }
  bcSurfRaf = requestAnimationFrame(step)
}
const globeSimDomain = computed(() => {
  const d = simDomain.value
  if (!d || bcSurfA.value >= 0.999) return d
  return { ...d, surfA: bcSurfA.value }
})
function bcRect(key: BcKey | null): { x: number; y: number; w: number; h: number } {
  const W = window.innerWidth
  const H = window.innerHeight
  if (!key) {
    // overview: the domain centred, a band on every side for the cards
    return { x: W * 0.29, y: 230, w: W * 0.42, h: Math.max(240, H - 230 - 190) }
  }
  // head-on: right of the docked card column
  const x0 = Math.min(W * 0.42, 600)
  return { x: x0, y: 150, w: W - x0 - 60, h: Math.max(240, H - 150 - 200) }
}
function applyBcView(durationMs: number): void {
  if (!bcSaved) return
  const lake = BC_LAKES[ch2ActiveLake.value]
  if (!lake) return
  const key = ch2BcFocus.value
  const wall = key === 'inflow' || key === 'outflow' || key === 'lat0' || key === 'lat1'
  const landedExag = bcSaved.exag ?? bcSaved.focus.focalExag ?? TRUE_EXAG * 2
  const exag = wall ? BC_WALL_EXAG : landedExag
  const v = bcView(lake, key ?? 'overview', {
    landedCamDir: focusCamDir(bcSaved.focus),
    exag,
    W: window.innerWidth,
    H: window.innerHeight,
    fovDeg: BC_FOV,
    rect: bcRect(key),
    durationMs,
    model: ch2FaceModel.value,
  })
  chapterExag.value = exag
  chapterFocus.value = v
  lerpBcSurfA(key === 'bed' ? 0.16 : 1)
}
function enterBcMode(): void {
  if (bcSaved || !chapterFocus.value) return
  bcSaved = { focus: { ...chapterFocus.value }, exag: chapterExag.value }
  ch2BcFocus.value = null
  applyBcView(1600)
}
function exitBcMode(): void {
  const saved = bcSaved
  bcSaved = null
  ch2BcFocus.value = null
  ch2BcHover.value = null
  lerpBcSurfA(1)
  if (!saved) return
  chapterExag.value = saved.exag
  chapterFocus.value = { ...saved.focus, durationMs: 1500 }
}
/** BC mode ends WITHOUT restoring (a section is re-framing anyway). */
function dropBcMode(): void {
  const saved = bcSaved
  bcSaved = null
  ch2BcFocus.value = null
  ch2BcHover.value = null
  cancelAnimationFrame(bcSurfRaf)
  bcSurfA.value = 1
  // the section's latest exaggeration (a wall view had lifted it)
  if (saved) chapterExag.value = saved.exag
  ch2BcOn.value = false
}
watch(ch2BcOn, (on) => {
  if (on) enterBcMode()
  else exitBcMode()
})
watch(ch2BcFocus, () => {
  if (ch2BcOn.value && bcSaved) applyBcView(1700)
})
// the elastic bed view sits lower (its pressure arrows are vertical)
watch(ch2FaceModel, () => {
  if (ch2BcOn.value && bcSaved && ch2BcFocus.value === 'bed') applyBcView(1100)
})
// Deep link: ?bc=1 lands in BC mode, ?bc=<inflow|outflow|lat0|lat1|bed|
// surface> on that boundary's head-on view (review / rehearsal links).
{
  const q = route.query.bc
  const want = typeof q === 'string' ? q : null
  if (want) {
    const stop = watch(
      () =>
        currentSection.value === 'chapter2' &&
        ch2IsImageryPhase(ch2PhaseNow.value) &&
        (simDomain.value?.carveT ?? 0) >= 0.999 &&
        !!chapterFocus.value,
      (ok) => {
        if (!ok) return
        stop()
        window.setTimeout(() => {
          ch2BcOn.value = true
          if ((BC_KEYS as string[]).includes(want)) {
            window.setTimeout(() => { ch2BcFocus.value = want as BcKey }, 1900)
          }
        }, 1200)
      },
    )
  }
}
function onBcResize(): void {
  if (ch2BcOn.value && bcSaved) applyBcView(300)
}
window.addEventListener('resize', onBcResize)
onBeforeUnmount(() => window.removeEventListener('resize', onBcResize))
// The model pills stay live in BC mode (the cards follow them); a
// lake change re-frames through SectionCh2 (→ dropBcMode).
// Catalog-lake hover/pin from the Globe raycaster + the phase panel.
const ch2LakeHover = ref<SimCatalogLake | null>(null)
const ch2LakePin = ref<SimCatalogLake | null>(null)
const ch2PhaseHoverNum = ref<number | null>(null)
const ch2CenterNum = computed(() => {
  // The MGSIM page is pinned to lake 1951 (its ensemble); Ch.2 follows
  // whichever lake was zoomed.
  const id = isMgsimPage.value ? 'CW2019_1951' : ch2ActiveLake.value
  const m = /_(\d+)$/.exec(id)
  return m ? parseInt(m[1], 10) : 2511
})
// The step on screen (config/ch2State.ts ch2StepShown): on every station
// beat, the station the view is (the beat's own or a click) — the single
// stress space beside the block draws it and the key names it.
const ch2Single = computed(() =>
  currentSection.value === 'chapter2' && ch2IsStationPhase(ch2PhaseNow.value) ? ch2StepShown(ch2View) : null,
)
const ch2HighlightNum = computed(
  () =>
    ch2PhaseHoverNum.value ??
    ch2LakeHover.value?.num ??
    ch2LakePin.value?.num ??
    null,
)

// ── Additional Work → MGSIM page ──
// The page re-uses the Ch.2 block machinery: its beat 0 = the landed
// pre-drainage block (Ch.2 beat 1), beat 1 = drained (Ch.2 beat 2).
// simLanded / simDrained gate the shared in-canvas pieces for both.
const mgsimBeat = ref(0)
const mgsimAdvanceTrigger = ref(0)
const simLanded = computed(() => isMgsimPage.value && mgsimBeat.value === 0)
const simDrained = computed(
  () =>
    (currentSection.value === 'chapter2' && ch2IsImageryPhase(ch2PhaseNow.value)) ||
    (isMgsimPage.value && mgsimBeat.value === 1),
)
function openAddlPage(page: AddlPage): void {
  if (page === 'deeper') {
    router.push({ name: 'additional-work-deeper', params: { chapter: 'chapter1' } })
    return
  }
  router.push({ name: `additional-work-${page}` })
}
function onDrainDomainClick(): void {
  if (isMgsimPage.value) mgsimAdvanceTrigger.value += 1
  else bumpBeatAdvance()
}
// What the MGSIM page needs from the shared in-canvas pieces
// (phase panel, lake card) — it emits this whenever its state changes.
const mgsimUi = ref<MgsimUiState | null>(null)
const mgsimPhaseUrl = mediaUrl('addl/mgsim/phase_space_mgsim.json')
// The Ch.2 ⇄ MGSIM handoff: the old section's unmount emits a null
// sim-domain that would tear the block down for a frame; while a
// handoff is pending that null is swallowed and the new section's
// first payload (same block, same framing) simply continues it.
let simHandoff = false
let simHandoffTimer: number | null = null
function armSimHandoff(): void {
  simHandoff = true
  if (simHandoffTimer !== null) window.clearTimeout(simHandoffTimer)
  simHandoffTimer = window.setTimeout(() => { simHandoff = false }, 4000)
}
// The Chapter 2 beat the bed-ensemble door was opened from — coming back
// through it lands there again when that was the second lake's walk.
let ch2DoorBeat: number | null = null
function openEnsembleFromCh2(): void {
  ch2DoorBeat = ch2FigurePass(ch2Beat.value) === 1 ? ch2Beat.value : null
  armSimHandoff()
  // The field travels only when a model is draped (imagery = the
  // page's default, the difference).
  const modelOn = ch2Face.value === 'elastic' || ch2Face.value === 'viscous'
  router.push({
    name: 'additional-work-mgsim',
    query: {
      from: 'ch2',
      field: modelOn ? ch2Field.value : 'difference',
      ...(ch2PhaseNow.value >= CH2_PHASE.post ? { drained: '1' } : {}),
    },
  })
}
function onMgsimExit(target: 'menu' | 'ch2'): void {
  if (target !== 'ch2') {
    exitTo('additional-work')
    return
  }
  navIntent = 'exit'
  // Back through the door: Ch.2 re-lands on lake 1951 in place (its
  // deep-link path), on the viscous face if a solution was up.
  armSimHandoff()
  const doorBeat = ch2DoorBeat
  ch2DoorBeat = null
  if (doorBeat !== null && ch2SecondLake.value === 'CW2019_1951') {
    // Opened on the second lake's walk (1951 second): back onto that
    // very beat; the first lake stays the visitor's.
    if (!mgsimUi.value?.drained) setCh2View(null)
    else setCh2View('post', 'imagery')
    settleIntent(router.push({ name: 'chapter2', query: { beat: String(doorBeat) } }))
    return
  }
  ch2SelectedLake.value = 'CW2019_1951'
  ch2SecondPick.value = null
  const drained = !!mgsimUi.value?.drained
  const field = mgsimUi.value?.field ?? 'difference'
  if (!drained) setCh2View(null)
  else if (mgsimUi.value?.solutionOn) {
    const v = ch2ViewOf('viscous', field)
    setCh2View(v.stage, v.layer)
  } else setCh2View('post', 'imagery')
  settleIntent(router.push({
    name: 'chapter2',
    query: drained
      ? { lake: 'CW2019_1951', drained: '1', field: ch2Field.value,
          ...(ch2Face.value === 'viscous' ? { model: 'viscous' } : {}) }
      : { lake: 'CW2019_1951', beat: String(CH2_BEAT.pre) },
  }))
}
function onMgsimBeatChange(beat: number): void {
  mgsimBeat.value = beat
  if (beat === 0) {
    setCh2View('post', 'imagery')
    ch2BcOn.value = false
    ch2LakeHover.value = null
    ch2LakePin.value = null
    ch2PhaseHoverNum.value = null
  }
}
// Deep-link/tooling params for the in-beat flow (?beat=1&drained=1&
// model=viscous&lake=CW2019_2394) — read once at setup so they're in
// place before SectionCh2 mounts and applies its beat.
{
  const q = route.query
  if (typeof q.lake === 'string' && /^CW2019_\d+$/.test(q.lake)) {
    ch2SelectedLake.value = q.lake
  }
  // ?drained=1 / ?model=... land on beat 2 (SectionCh2 maps the beat);
  // the view follows the model (+ ?field=) when one is named, and the
  // tiers' own words ?stage=&layer= win over both.
  const field: SimField =
    q.field === 'nopatch' || q.field === 'patch' || q.field === 'difference'
      ? q.field
      : 'difference'
  if (q.model === 'elastic' || q.model === 'viscous') {
    const v = ch2ViewOf(q.model, field)
    setCh2View(v.stage, v.layer)
  } else {
    setCh2View(null)
  }
  if (q.stage === 'pre' || q.stage === 'post' || q.stage === 'difference') {
    const layer =
      q.layer === 'imagery' || q.layer === 'elastic' || q.layer === 'viscous'
        ? q.layer
        : undefined
    setCh2View(q.stage, layer)
  }
}
// Shared payload type (config/simLakes.ts) — Ch.2 and the MGSIM page
// both emit it; Globe consumes it.
const simDomain = ref<import('../config/simLakes').SimDomainPayload | null>(null)
function onSimDomain(target: typeof simDomain.value): void {
  if (target === null && simHandoff) return
  if (target !== null && simHandoff) {
    simHandoff = false
    if (simHandoffTimer !== null) { window.clearTimeout(simHandoffTimer); simHandoffTimer = null }
  }
  simDomain.value = target
}

function onCh2BeatChange(beat: number, isLast: boolean): void {
  beatReportedFor.value = 'chapter2'
  ch2Beat.value = beat
  ch2IsLastBeat.value = isLast
  if (ch2Phase(beat) !== CH2_PHASE.lakes && lakeVideo.value !== null) {
    lakeVideo.value = null
  }
  // Back to the lakes overview: next zoom starts fresh pre-drainage
  // (SectionCh2 clears the block view itself).
  const ph = ch2Phase(beat)
  if (ph === CH2_PHASE.lakes) {
    ch2BcOn.value = false
    // NEXT opens the chapter's lake movie (2 s to its first frame, cold).
    warmPlain(mediaUrl(`ch02/lakes_valid/${ch2SelectedLake.value}.mp4`))
  }
  // The population, theory and implications beats are narrated at length:
  // warm Chapter 3's opening movies into the HTTP cache meanwhile (from the
  // population page on — the slab's run is on the GPU since the bed beat).
  if (ph >= CH2_PHASE.population) warmCh3Openers()
  // BC mode belongs to the block beats (zoom + drain): NEXT into the
  // bed or the results leaves it, restoring the landed framing.
  if (!ch2IsImageryPhase(ph) && ch2BcOn.value) ch2BcOn.value = false
  // EVERY beat change clears the catalog hover/pin state (a symbol once
  // kept its gold outline after the pointer left —
  // nothing hover-driven may outlive the beat it was made on).
  ch2LakeHover.value = null
  ch2LakePin.value = null
  ch2PhaseHoverNum.value = null
}

// ── Ch.3 wiring ──
const ch3Beat = ref(0)
function onCh3BeatChange(beat: number, isLast: boolean): void {
  beatReportedFor.value = 'chapter3'
  ch3Beat.value = beat
  ch3IsLastBeat.value = isLast
}

// "Zoom in": remember which lake and step to the zoom beat — one user
// action (the beat change closes the dock).
function drainSelectedLake(): void {
  if (lakeVideo.value) setCh2Lake(lakeVideo.value.id)
  // The popup stays up for this tick: SectionCh2's NEXT reads "a popup is
  // open" as "zoom" (no popup = open one first), and the beat change
  // closes it (onCh2BeatChange). Same step as the NEXT pill.
  ch2AdvanceTrigger.value += 1
}

// Clicking empty globe closes the video dock (the imagery box used to
// linger when the visitor clicked on other things).
function onCanvasBlankClick(): void {
  if (lakeVideo.value !== null) lakeVideo.value = null
}

// Leaving the section (top-nav, menu, browser nav) also dismisses it.
watch(currentSection, () => {
  ch1PrevBeat = -1
  beatReportedFor.value = null
  beatJump.value = null
  lakeVideo.value = null
  featuredPulseId.value = null
  featuredHoverId.value = null
  ch3LakeClick.value = null
})

const velocityMode = ref<{
  active: boolean
  dataUrl?: string
  highlightColor?: string
} | null>(null)
function onVelocityMode(target: typeof velocityMode.value): void {
  velocityMode.value = target
}

// Generic chapter colormap drape. Ch.1 no longer uses it (the twin
// globes replaced the single-drape closer) — kept for future chapters.
const chapterOverlay = ref<{ url: string; opacity?: number } | null>(null)

// Cross-section slab effects (drain + paint + morph spin/level) + the
// theory-panel stage.
const slabFx = ref<{
  fracTLon: number
  drainT: number
  paintT?: number
  paintUrl?: string
  spinT?: number
  levelT?: number
  cropT?: number
} | null>(null)
function onSlabFx(target: typeof slabFx.value): void {
  slabFx.value = target
}

const theoryStage = ref<number | null>(null)
function onTheoryStage(value: number | null): void {
  theoryStage.value = value
}

// Current Ch.1 beat (SectionCh1's beat-change emit) — scopes the beat
// chrome: the drainage legend (0), the slab action buttons (1–3), the
// τxx colour scale (3), the theory panel and twin globes afterwards.
const ch1Beat = ref(0)
// TwinGlobes used to mount the moment the ACL beat arrived —
// two full 3D scenes building on that entry frame was the "screen
// freezes going into the ACL section". Now they mount ~1.5 s AFTER the
// maps beat lands, during idle; reaching the twins beat forces it.
const twinsMountReady = ref(false)
let twinsMountTimer: number | null = null
watch(
  () => [currentSection.value, ch1Beat.value] as const,
  ([sec, beat]) => {
    if (sec !== 'chapter1' || beat < ch1First('maps')) {
      if (twinsMountTimer !== null) {
        window.clearTimeout(twinsMountTimer)
        twinsMountTimer = null
      }
      if (sec !== 'chapter1') twinsMountReady.value = false
      return
    }
    if (twinsMountReady.value) return
    if (beat >= ch1First('twins')) {
      twinsMountReady.value = true
    } else if (twinsMountTimer === null) {
      twinsMountTimer = window.setTimeout(() => {
        twinsMountReady.value = true
        twinsMountTimer = null
      }, 1500)
    }
  },
)

// τxx colour scale: the paint beat only — it leaves as the TOY MODEL
// click starts the 3→4 morph (a bottom-centre bar would otherwise sit
// over the slab while the camera dives it into the theory panel).
const showStressLegend = computed(
  () =>
    currentSection.value === 'chapter1' &&
    ch1Beat.value === ch1First('paint') &&
    theoryStage.value === null &&
    (slabFx.value?.paintT ?? 0) > 0.05,
)

// Chapter-driven vertical exaggeration. Null = use Globe's default
// TARGET_EXAGGERATION (≈90×); a number value lerps the dome's vertical
// scale to that fraction. SectionCh1 sets ≈0.0028 (≈10×) on mount.
const chapterExag = ref<number | null>(null)
function onChapterExag(value: number | null): void {
  // Same handoff guard as onChapterFocus: the old chapter's unmount
  // null would lerp the dome back to 90× for a beat (visible pump).
  if (
    value === null &&
    (currentSection.value === 'chapter1' ||
      currentSection.value === 'chapter2' ||
      currentSection.value === 'chapter3' ||
      isMgsimPage.value ||
      isRevisitPage.value)
  ) {
    return
  }
  // BC mode owns the exaggeration while it is up (a head-on wall view
  // lifts it): a section's new value becomes the one restored on exit.
  if (value !== null && ch2BcOn.value && bcSaved) {
    bcSaved.exag = value
    applyBcView(900) // (the landed exaggeration may have just settled)
    return
  }
  chapterExag.value = value
}

// Top-left scale-reference card opacity. Fades in over the last 25%
// of the cut sweep, capped so it doesn't compete with the cross-
// section + WTC inset for attention.
const scaleReferenceOpacity = computed(() =>
  Math.max(0, Math.min(1, (rollbackProgress.value - 0.75) / 0.25)) * 0.92,
)

// Per-section camera tilt override. The Introduction dips the camera
// lower (~35°) so the cross-section reveal reads with depth; other
// sections (and the menu) use Globe's default 50°.
const cameraTilt = computed<number | undefined>(() => {
  if (currentSection.value === 'introduction') return 35
  return undefined
})

const sectionLabel = computed(
  () => sectionById(currentSection.value)?.label ?? ''
)
// The talk spine (next-section ordering) is navSections' array order —
// config/sitePath.ts reads it for the shared pills.

const MENU_REVEAL_DELAY_MS = 7400

let menuRevealTimer: number | null = null
function scheduleMenuReveal(): void {
  if (menuRevealTimer !== null) window.clearTimeout(menuRevealTimer)
  menuRevealTimer = window.setTimeout(() => {
    // Only flip to /menu if we're still in the post-intro spin state.
    // If the user pushed back to home or navigated to a section via
    // browser controls, don't override their navigation.
    if (appMode.value === 'globe') returnToMenu()
    menuRevealTimer = null
  }, MENU_REVEAL_DELAY_MS)
}

// Route → state sync. Each meaningful UI state has its own URL so
// refresh and direct links land in the right place:
//   /                  → intro splash (Greenland clickable)
//   /menu              → vertical chapter menu
//   /<section-id>      → that section directly
// User actions (clicking Greenland, picking a card, top-nav, "back")
// push to the router; the watcher below mirrors that into appMode +
// currentSection so every component sees one consistent state.
function syncFromRoute(name: string | symbol | null | undefined): void {
  const n = typeof name === 'string' ? name : ''
  const addl = ADDL_PAGES.find((p) => n === `additional-work-${p}`) ?? null
  addlPage.value = addl
  if (addl) {
    appMode.value = 'section'
    currentSection.value = 'additional-work'
    baseClicks.value = Math.max(1, baseClicks.value)
    sectionGlobeOverride.value = null
    showArrows.value = false
    return
  }
  if (n === 'menu') {
    appMode.value = 'menu'
    currentSection.value = null
    baseClicks.value = Math.max(1, baseClicks.value)
    sectionGlobeOverride.value = null
    showArrows.value = false
    return
  }
  if (n && SECTIONS.some((s) => s.id === n)) {
    if (appMode.value === 'menu' && STAGE_FIT_HOLD_SECTIONS.includes(n)) holdStageFit()
    appMode.value = 'section'
    currentSection.value = n as SectionId
    baseClicks.value = Math.max(1, baseClicks.value)
    sectionGlobeOverride.value = null
    showArrows.value = false
    return
  }
  // 'home' or anything unrecognised → intro splash + fully reset state.
  if (menuRevealTimer !== null) {
    window.clearTimeout(menuRevealTimer)
    menuRevealTimer = null
  }
  appMode.value = 'intro'
  currentSection.value = null
  baseClicks.value = 0
  sectionGlobeOverride.value = null
  showArrows.value = false
  rollbackProgress.value = 0
}

watch(() => route.name, (n) => syncFromRoute(n))

// Sync state from the URL at setup-time, NOT onMounted. Globe.vue mounts
// before its parent (children-before-parents in Vue), so if we waited for
// onMounted to run syncFromRoute, Globe would already have called
// applyClickState(0) (spinning Earth) before clicks=1 arrives — then the
// 7-second opening animation has to run before /menu or /<section> shows
// Greenland. Doing it here means baseClicks is set BEFORE Globe mounts,
// so Globe.onMounted's `if (props.clicks >= 1) applyClickState(...)` path
// fires immediately. No black-screen wait for deeplinks.
syncFromRoute(route.name)

function beginTour(): void {
  // User clicked Greenland on the intro splash. Spin the globe locally
  // (URL stays at '/') and schedule the URL flip to '/menu' once the
  // settling animation finishes.
  baseClicks.value = 1
  appMode.value = 'globe'
  scheduleMenuReveal()
}

function returnToGlobe(): void {
  // Cancel any pending menu reveal first; the route sync resets the
  // rest of the state when '/' arrives.
  if (menuRevealTimer !== null) {
    window.clearTimeout(menuRevealTimer)
    menuRevealTimer = null
  }
  navIntent = 'path'
  settleIntent(router.push({ name: 'home' }))
}

// The path's own moves (the ribbon, the menu, the pills) — they clear the
// door trail.
function returnToMenu(): void {
  navIntent = 'path'
  settleIntent(router.push({ name: 'menu' }))
}

function selectSection(id: SectionId): void {
  navIntent = 'path'
  settleIntent(router.push({ name: id }))
}

function onGlobeClicks(value: number): void {
  // A section component is requesting a specific Globe state for one of
  // its internal steps (e.g. Motivation step 1 wants streamlines).
  sectionGlobeOverride.value = value
}

function onShowArrows(value: boolean): void {
  showArrows.value = value
}

function onRollbackProgress(value: number): void {
  rollbackProgress.value = value
}

// Introduction · literature timeline (null = layer hidden, 0 = the first
// visit, 1 = the revisit after the coupling-length step).
const introTimelineStep = ref<number | null>(null)

// The takeaway beat (the director's design: on each chapter's final NEXT
// everything fades into the background and the chapter's main takeaway is
// highlighted, the card it sits in growing a little). Each chapter's last
// beat (`takeaway` in its registry):
// the line already on its implications page grows out of its spot into
// the centred card. The Introduction has no extra step — its last step
// (timeline2, Rines 2026 lit as "Chapter 1") pops its question, with the
// lit card kept bright through the dim. Up only once the page has
// reported the beat; GROWS when the press came from the beat before
// (NEXT), lands settled otherwise (a deep link, BACK from the next page).
interface TakeawayPopCfg {
  text: string
  source: string | null
  spotlight: string[][] | null
  place: 'center' | 'low'
  delayMs: number
}
const takeawayPop = computed<TakeawayPopCfg | null>(() => {
  const sec = currentSection.value
  if (appMode.value !== 'section' || !sec || beatReportedFor.value !== sec) return null
  switch (sec) {
    case 'introduction':
      return introBeat.value === INTRO_STEP.timeline2 && introTimelineStep.value === 1
        ? {
            text: INTRO_TAKEAWAY,
            source: null,
            // the lit Rines 2026 card stays bright: its page and its pill,
            // each a hole of its own shape (one box round both showed as a
            // lit rectangle, far too strong)
            spotlight: [['.lt-paper.hot .lt-page'], ['.lt-paper.hot .lt-label']],
            place: 'low',
            // the highlight lands first (the timeline fades in, the card lifts)
            delayMs: 900,
          }
        : null
    case 'chapter1':
      // down through the close-out AND the post-route linger: the gap
      // between `ch1TwinsClosing` clearing and the route landing popped
      // it back for a frame, and its 0.6 s fade-out rode over Chapter 2
      return ch1Beat.value === ch1First('takeaway') && !ch1TwinsClosing.value && !twinsLinger.value
        ? { text: CH1_TAKEAWAY, source: '.tg-takeaway', spotlight: null, place: 'center', delayMs: 0 }
        : null
    case 'chapter2':
      return ch2IsTakeaway(ch2Beat.value)
        ? { text: CH2_TAKEAWAY, source: '.im-takeaway', spotlight: null, place: 'center', delayMs: 0 }
        : null
    case 'chapter3':
      return ch3Beat.value === ch3First('takeaway')
        ? { text: CH3_TAKEAWAY, source: '.ci-takeaway', spotlight: null, place: 'center', delayMs: 0 }
        : null
    default:
      return null
  }
})
// The words + placement outlive the beat through the card's exit.
const takeawayPopText = ref<TakeawayPopCfg>({ text: '', source: null, spotlight: null, place: 'center', delayMs: 0 })
const takeawayPopAnimate = ref(false)
watch(takeawayPop, (cfg) => { if (cfg) takeawayPopText.value = cfg }, { immediate: true, flush: 'sync' })
// NEXT from the beat before (same page, one beat back, both reported)
// grows it; any other arrival lands it settled.
watch(
  () => [currentSection.value, activeBeat.value, beatReportedFor.value] as const,
  ([sec, beat, rep], old) => {
    takeawayPopAnimate.value = !!old && rep === sec && old[2] === sec && old[0] === sec && old[1] === beat - 1
  },
  { immediate: true, flush: 'sync' },
)
function onTimelineStep(value: number | null): void {
  introTimelineStep.value = value
}
// The first visit's walk: the paper NEXT has reached (null = none yet).
const introTimelinePaper = ref<string | null>(null)
// The four-papers step: the coupling step's four papers lit in their colours.
const introTimelineFocus = ref(false)

// Introduction · the fly-along: the flat-map layer's state
// (mounted / revealed / the landing view) plus the three intro-only
// Globe knobs SectionMotivation drives during the dive.
const introFieldwork = ref<FieldworkLayerState | null>(null)
// True while that map is fully revealed — opaque over the whole screen — so
// the Globe idles under it (Globe's `covered`: frames it rendered
// unseen at 60 fps queued up in the GPU process and froze the screen for
// 3–6 s when the map left).
const introMapCovering = ref(false)
// Introduction · the seasons (steps 2–3): which map the month drape wears
// (null = not on those steps) — the colorbar follows it.
const introSeasonView = ref<'speed' | 'anom' | null>(null)
const chapterExagMs = ref<number>(1500)
const stripVelocity = ref(false)
const hillshade = ref<number | null>(null)
// The Introduction's step-0 measuring lines + sea-level label: points
// the Globe projects to screen every frame (window.__globeAnchorScreens).
const screenAnchors = ref<{ id: string; lat: number; lon: number; lift?: number; surface?: boolean }[] | null>(null)
const fieldworkPatch = ref<{
  url: string
  latC: number
  lonC: number
  halfXm: number
  halfYm: number
  rEarthM: number
  opacity: number
} | null>(null)

function advanceSection(): void {
  // Section says "I'm done, jump to the next page" — the site path
  // (config/sitePath.ts, = navSections order); past the last page, the
  // menu. A door page counts as Additional Work, so its next is Repos.
  const next = pathNext(currentSection.value)
  if (next) selectSection(next)
  else returnToMenu()
}

watch(
  () => baseClicks.value,
  (n) => {
    if (n < 1) {
      appMode.value = 'intro'
      currentSection.value = null
      sectionGlobeOverride.value = null
    }
  }
)
</script>

<style scoped>
.explore {
  position: relative;
  width: 100%;
  height: 100%;
  background: #000;
  overflow: hidden;
  /* The sub-menu bar under the ribbon (BeatLandmarks): its gap below
     the ribbon and its height. */
  --lm-gap: 0.3rem;
  --lm-h: 2rem;
  /* The ribbon's measured height (the director asked for a touch larger,
     slightly thicker outlines — 2.86rem → 2.92rem, measured 46.8 px). */
  --nav-h: 2.92rem;
  /* The back/next pair's footprint (two 6.4rem pills + the 0.5rem gap):
     the sub-menu keeps clear of it when the pills drop to its row. */
  --pills-w: 13.3rem;
}
/* While a beat page's sub-menu hangs under the ribbon, the top chrome
   ends at its bottom edge: ribbon 1.2vh + 2.86rem (measured 45.8 px) +
   the bar (--nav-h). Overlays that open under the chrome start at
   max(<their own top>, var(--chrome-bottom) + 0.75rem) — unset (0) on
   every other page, so they keep their own top there. */
.explore.with-landmarks {
  --chrome-bottom: calc(1.2vh + var(--nav-h) + var(--lm-gap) + var(--lm-h));
}

/* ------------------------------------------------------------------ */
/* INTRO overlay — title + Click to begin.                              */
/* ------------------------------------------------------------------ */
.intro-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  padding: 0 0 12vh 0;
  pointer-events: none;
}

.intro-title {
  font-family: 'EB Garamond', serif;
  font-weight: 400;
  /* 88 characters on two lines, set in caps like a title
     page (the thesis sets it in caps; title case is one line here if
     preferred: drop text-transform, letter-spacing back to 0.01em). */
  font-size: clamp(1.2rem, 2.3vw, 2.25rem);
  line-height: 1.25;
  margin: 0 0 0.6rem 0;
  padding: 0 4vw;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  text-align: center;
  text-shadow: 0 2px 18px rgba(0, 0, 0, 0.7);
  color: var(--fg);
}

.intro-title-line {
  display: block;
}

.intro-sub {
  font-size: clamp(0.9rem, 1.2vw, 1.1rem);
  margin: 0 0 2.5rem 0;
  opacity: 0.75;
  letter-spacing: 0.04em;
  text-shadow: 0 1px 10px rgba(0, 0, 0, 0.7);
}

.intro-hint {
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 0.95rem;
  letter-spacing: 0.06em;
  margin: 0;
  color: var(--gold);
  text-shadow: 0 1px 14px rgba(0, 0, 0, 0.7);
  animation: hint-pulse 2.6s ease-in-out infinite;
}

@keyframes hint-pulse {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1.0; }
}

/* Logo row — pinned to the top-left of the viewport. Hover dims     */
/* neighbours, brightens the focused logo. Clicks open in a new tab. */
.logo-row {
  position: absolute;
  top: 2.4vh;
  left: 2vw;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 1.4rem;
  pointer-events: auto;
}

.logo-link {
  display: inline-flex;
  align-items: center;
  height: 56px;
  opacity: 0.78;
  transition: opacity 0.25s, transform 0.25s, filter 0.25s;
  filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.6));
}

.logo-link img {
  height: 100%;
  width: auto;
  display: block;
}

.logo-row:hover .logo-link {
  opacity: 0.4;
}

.logo-row .logo-link:hover {
  opacity: 1.0;
  transform: translateY(-2px);
  filter: drop-shadow(0 3px 14px rgba(255, 200, 60, 0.4));
}

/* Persona row — the logo row's mirror in the top-right:               */
/* LinkedIn + GitHub marks in off-white, the GitHub avatar as a disc.  */
.persona-row {
  position: absolute;
  top: 2.4vh;
  right: 2vw;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 1.1rem;
  pointer-events: auto;
}

.persona-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  color: var(--fg);
  opacity: 0.78;
  transition: opacity 0.25s, transform 0.25s, filter 0.25s;
  filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.6));
}

.persona-link svg {
  width: 30px;
  height: 30px;
  fill: currentColor;
  display: block;
}

.persona-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: block;
  object-fit: cover;
  border: 1px solid rgba(245, 245, 245, 0.35);
  filter: grayscale(0.55);
  transition: filter 0.25s;
}

.persona-row:hover .persona-link {
  opacity: 0.4;
}

.persona-row .persona-link:hover {
  opacity: 1.0;
  transform: translateY(-2px);
}

.persona-row .persona-link:hover .persona-avatar {
  filter: grayscale(0);
}

/* ------------------------------------------------------------------ */
/* Scale-reference card (top-left, Motivation only) — flat USA basemap */
/* with Greenland silhouette overlaid in gold. Greenland's relative   */
/* dimensions vs the contiguous USA: ~24% as wide, ~92% as tall.      */
/* The director found the card too small (half the size wanted): every */
/* length below doubled — 320 × 169 → 640 × 338, the silhouette's box  */
/* and offsets with it, so the proportions are exactly the old ones.   */
/* ------------------------------------------------------------------ */
.scale-reference {
  position: absolute;
  /* Under the ribbon's sub-menu (--chrome-bottom, set on .explore while
     the bar hangs there). (Was 7vh, which the bar's left half crossed at
     1440 and 1920.) Set 8 % smaller from its corner so, that much lower,
     its bottom-right corner still clears the 2,670 km rule's west end
     (1440 × 900). */
  top: max(7vh, calc(var(--chrome-bottom, 0px) + 0.75rem));
  transform: scale(0.92);
  transform-origin: top left;
  left: 2vw;
  width: 640px;
  pointer-events: none;
  transition: opacity 0.5s;
  z-index: 8;
}

/* Card sized to the cropped Albers Equal-Area USA image
   (3600×1906 → 1.889:1 aspect → 640 × 338 px). Cropped PNG removes
   the black top/bottom margins matplotlib left around the projected
   CONUS, so there's no gap between the gold border and the imagery. */
.scale-reference-frame {
  position: relative;
  width: 640px;
  height: 338px;
  border: 1px solid var(--gold-faint);
  border-radius: 8px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.5);
  box-shadow:
    0 4px 22px rgba(0, 0, 0, 0.6),
    inset 0 0 18px rgba(184, 115, 51, 0.06);
  backdrop-filter: blur(2px);
}

/* USA basemap (Albers Equal-Area, cropped tight): fills the card. */
.scale-reference-frame .usa-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  filter: saturate(0.55) brightness(0.7);
  opacity: 0.85;
}

/* Greenland silhouette: sized to real Greenland-vs-USA proportions
   from the two equal-area projections, its SOUTH tip near the southern
   tip of Texas on the basemap (placement only — the comparison is the
   size). The numbers (re-derived from the build scripts,
   cinematic/scene_01_intro/build_{usa_basemap,greenland_silhouette}.py):
     USA Albers, lon −126…−66 × lat 24…50 → a 6098 × 3227 km projected
       box on the 3600 × 1906 px PNG; on the 640 px card 9.53 km/px.
     Greenland LAEA, Natural Earth 10m, 979 × 1785 px at 1.4923 km/px →
       1461 × 2664 km (2.18 M km²) → 153.3 × 279.6 px on the card.
   The GOLD is Greenland at that size (154 × 280, aspect = the PNG's);
   the black layer is the same mask scaled ×1.039 for a ~3 px rim.
   (Before that re-derivation the box was 154 × 270 — 3.5 % short, so the mask
   was squashed — and the gold a further 5 % inside it.) */
.scale-reference-frame .greenland-silhouette {
  position: absolute;
  width: 160px;
  height: 291px;
  left: calc(50% - 80px);
  top: 24px;
  -webkit-mask-image: var(--silhouette-url);
  -webkit-mask-size: 100% 100%;
  -webkit-mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-image: var(--silhouette-url);
  mask-size: 100% 100%;
  mask-repeat: no-repeat;
  mask-position: center;
}

/* Black rim layer: the mask ×1.039, behind the gold fill. */
.greenland-outline {
  background: black;
  filter: drop-shadow(0 0 1px rgba(0, 0, 0, 1))
          drop-shadow(0 0 1px rgba(0, 0, 0, 1));
  z-index: 1;
}

/* Gold fill = Greenland at the card's true scale (see above); the
   black shows round it as a rim. */
.greenland-fill {
  background: var(--gold-bright);
  width: 154px;
  height: 280px;
  left: calc(50% - 77px);
  top: 29px;
  filter: drop-shadow(0 0 6px rgba(244, 207, 106, 0.55));
  z-index: 2;
}

.scale-reference-caption {
  margin-top: 0.5rem;
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 1rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--gold);
  text-align: center;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.7);
}

/* ------------------------------------------------------------------ */
/* MENU panel — vertical, right side. All 6 cards fit without scroll;   */
/* "Return to globe" lives outside as a floating top-left button.       */
/* ------------------------------------------------------------------ */
.menu-panel {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  /* MENU_STAGE_FIT mirrors this width (the object is fitted beside it). */
  width: 48vw;
  max-width: 620px;
  display: flex;
  flex-direction: column;
  /* Pin to top with breathing room from the viewport edges so all
     six cards have the full vertical space to share equally. */
  padding: 2.4vh 3vw 1.6vh 1.5vw;
  pointer-events: auto;
}

/* Floating "Return to globe" — top-left of viewport, replaces the
   in-panel header so the menu panel can be tighter. */
.menu-back-floating {
  position: absolute;
  top: 1.6vh;
  left: 1.6vh;
  background: rgba(0, 0, 0, 0.55);
  border: 1px solid var(--gold-faint);
  color: var(--gold-dim);
  font-family: inherit;
  font-size: 0.82rem;
  letter-spacing: 0.04em;
  padding: 0.45rem 0.95rem;
  border-radius: 999px;
  cursor: pointer;
  z-index: 10;
  backdrop-filter: blur(8px);
  transition: color 0.2s, border-color 0.2s, background 0.2s;
}

.menu-back-floating:hover {
  color: var(--gold-bright);
  border-color: var(--gold);
  background: rgba(36, 24, 8, 0.75);
}

/* Cards share available vertical space equally via flex:1. With 6
   cards in the panel and no header chrome, each card auto-sizes to
   fit, no scrollbar. Width drives the visible imagery aspect. */
.menu-list {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  flex: 1 1 auto;
  min-height: 0;
}

.menu-aux {
  display: flex;
  gap: 1.2rem;
  margin-top: 0.8rem;
  padding-top: 0.6rem;
  border-top: 1px solid var(--gold-faint);
}

.menu-aux-btn {
  background: transparent;
  border: none;
  color: var(--gold-dim);
  font-family: inherit;
  font-size: 0.85rem;
  letter-spacing: 0.05em;
  padding: 0.25rem 0;
  cursor: pointer;
  transition: color 0.2s ease;
}

.menu-aux-btn:hover {
  color: var(--gold-bright);
}

/* The thesis | beyond break, in the menu's aux row. */
.menu-aux-sep {
  width: 1px;
  align-self: stretch;
  background: var(--gold-faint);
}

/* ------------------------------------------------------------------ */
/* TOP NAV — golden pill row with a "Menu" back-button at the start.   */
/* ------------------------------------------------------------------ */
/* The wrapper carries the placement (shrink-wraps the ribbon); the
   sub-menu hangs from its bottom edge (BeatLandmarks). */
.top-nav-wrap {
  position: absolute;
  top: 1.2vh;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
}
.top-nav {
  display: flex;
  gap: 0.3rem;
  background: rgba(0, 0, 0, 0.6);
  /* 1 px gold-faint → 1.5 px, half again as strong (projector contrast) */
  border: 1.5px solid rgba(232, 185, 74, 0.38);
  border-radius: 999px;
  padding: 0.35rem 0.4rem;
  backdrop-filter: blur(10px);
  pointer-events: auto;
}

.nav-btn {
  background: transparent;
  border: 1.5px solid transparent;
  color: rgba(232, 185, 74, 0.85);
  font-family: inherit;
  /* 0.78rem → 0.92rem (12.5 → 14.7 px), tracking 0.03 → 0.02em and the
     side padding 0.65 → 0.55rem keep the bar inside a 1280-wide window
     (the director asked for a touch larger, slightly thicker outlines). */
  font-size: 0.92rem;
  font-weight: 500;
  letter-spacing: 0.02em;
  /* 0.95rem → 0.65rem, tracking 0.05 → 0.03em: the
     three stage labels + the Repos pill widened the bar ~260 px; this
     claws ~120 back so it still fits a 1440-wide window with margin. */
  padding: 0.4rem 0.55rem;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s, border-color 0.2s;
  white-space: nowrap;
}

.nav-btn:hover {
  color: var(--gold-bright);
  background: var(--gold-faint);
}

.nav-btn.active {
  color: #fff8d8;
  background: var(--gold-faint);
  border-color: var(--gold);
}

.nav-btn.nav-back {
  font-size: 1.12rem;
  padding: 0.3rem 0.75rem;
  margin-right: 0.3rem;
  border-right: 1.5px solid rgba(232, 185, 74, 0.38);
  border-radius: 0;
}

.nav-btn.nav-back:hover {
  background: transparent;
  color: var(--gold-bright);
}

/* The thesis | beyond break — the same 1 px gold-faint rule
   the ☰ button already draws on its right, standing between pills. */
.nav-sep {
  width: 1.5px;
  align-self: stretch;
  margin: 0 0.3rem;
  background: rgba(232, 185, 74, 0.38);
}

/* The sub-menu under the ribbon (BeatLandmarks): fades between pages. */
.landmarks-fade-enter-active,
.landmarks-fade-leave-active {
  transition: opacity 0.35s ease;
}
.landmarks-fade-enter-from,
.landmarks-fade-leave-to {
  opacity: 0;
}

/* ------------------------------------------------------------------ */
/* Ch.1 beat navigation — top-right pills beside the top nav.          */
/* ------------------------------------------------------------------ */
.beat-nav {
  position: absolute;
  /* Vertically centred on the ribbon (--nav-h), each pill as tall as the
     sub-menu bar (--lm-h). */
  top: calc(1.2vh + (var(--nav-h) - var(--lm-h)) / 2);
  right: 2vw;
  display: flex;
  gap: 0.5rem;
  z-index: 11;
  pointer-events: auto;
}

/* On narrower viewports the centred ribbon reaches the pills' slot —
   they drop to the sub-menu's row instead (level with it, at its right;
   BeatLandmarks pulls its right end in to clear them). History: 1650 →
   1840 (the stage labels + the Repos pill) → 1560 (bar 990 px) → 1680
   (the larger ribbon: 1070 px wide; the pills need
   0.48·W ≥ bar/2 + pills + 16 px → W ≥ ~1600, kept with margin).
   Re-measure .top-nav vs .beat-nav at 1280 / 1440 / 1920 after ANY
   ribbon change. */
@media (max-width: 1680px) {
  .beat-nav { top: calc(1.2vh + var(--nav-h) + var(--lm-gap)); }
}

.beat-btn {
  background: rgba(0, 0, 0, 0.6);
  border: 1.5px solid rgba(232, 185, 74, 0.45);
  color: rgba(232, 185, 74, 0.9);
  font-family: 'Inter', system-ui, sans-serif;
  /* 0.78rem → 0.9rem (12.5 → 14.4 px), 1 → 1.5 px outline (projector
     legibility) */
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  height: var(--lm-h);
  padding: 0;
  /* Fixed footprint so "next →" and "Ch. 2 →" occupy the same pill —
     the label swap on the last beat must not shift the buttons. */
  width: 6.4rem;
  text-align: center;
  border-radius: 999px;
  cursor: pointer;
  backdrop-filter: blur(10px);
  transition: color 0.2s, border-color 0.2s, background 0.2s;
  white-space: nowrap;
}


.beat-btn-back {
  border-color: rgba(255, 255, 255, 0.36);
  color: rgba(245, 245, 245, 0.8);
}
.beat-btn-back:hover {
  color: rgba(245, 245, 245, 1);
  border-color: rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.04);
}

.beat-btn-next:hover {
  color: var(--gold-bright);
  border-color: var(--gold);
  background: rgba(36, 24, 8, 0.75);
}

/* ------------------------------------------------------------------ */
/* SECTION panel.                                                       */
/* ------------------------------------------------------------------ */
.section-panel {
  position: absolute;
  top: 7vh;
  right: 0;
  bottom: 4vh;
  width: 40vw;
  max-width: 580px;
  padding: 0 3vw 0 2.5vw;
  overflow-y: auto;
  pointer-events: auto;
}

/* ------------------------------------------------------------------ */
/* Transitions                                                          */
/* ------------------------------------------------------------------ */
.intro-fade-enter-active,
.intro-fade-leave-active {
  transition: opacity 0.6s;
}
.intro-fade-enter-from,
.intro-fade-leave-to {
  opacity: 0;
}

.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity 0.6s, transform 0.6s;
}
.menu-fade-enter-from {
  opacity: 0;
  transform: translateX(20px);
}
.menu-fade-leave-to {
  opacity: 0;
  transform: translateY(-30px);
}

.topnav-fade-enter-active,
.topnav-fade-leave-active {
  transition: opacity 0.45s, transform 0.45s;
}
.topnav-fade-enter-from {
  opacity: 0;
  transform: translate(-50%, -120%);
}
.topnav-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, -120%);
}

.section-fade-enter-active,
.section-fade-leave-active {
  transition: opacity 0.4s;
}
.section-fade-enter-from,
.section-fade-leave-to {
  opacity: 0;
}

/* (The theory panel manages its own show/hide opacity — it stays
   mounted from beat 3 on so its heavy first paint never lands mid-
   choreography.) */
</style>
