'use strict';

const status = document.getElementById('status');
const studies = document.getElementById('studies');

function cell(tag, value) {
  const element = document.createElement(tag);
  element.textContent = value;
  return element;
}

function renderStudy(study) {
  const article = document.createElement('article');
  article.append(cell('h2', study.title), cell('p', study.scope));
  article.append(cell('p', `Source frames ${study.frames_inclusive[0]}–${study.frames_inclusive[1]} · ${study.fps_nominal.toFixed(2)} fps`));
  const useStatus = cell('p', `Source use: ${study.source_use_status}; privacy review: ${study.privacy_review_status}. Local case study only.`);
  useStatus.className = 'scope';
  article.append(useStatus);
  if (study.candidate_box_player_frames != null) {
    article.append(cell('p', `${study.candidate_box_player_frames}/${study.candidate_box_total_player_frames} named player-frame boxes usable; all six boxes together on ${study.all_six_box_frames} frames.`));
  }
  const table = document.createElement('table');
  table.append(document.createElement('thead'), document.createElement('tbody'));
  const heading = document.createElement('tr');
  heading.append(cell('th', 'Player'), cell('th', 'Approximate distance'), cell('th', 'Frames'));
  table.tHead.append(heading);
  for (const distance of study.distances) {
    const row = document.createElement('tr');
    const interval = distance.frames_inclusive;
    row.append(cell('td', distance.player),
      cell('td', `${distance.approximate_distance_m.toFixed(distance.scope === 'endpoint_chord_scoped_estimate' ? 2 : 1)} m`),
      cell('td', `${interval[0]}–${interval[1]}${distance.scope === 'post_landing_segment' ? ' (post-landing only)' : distance.scope === 'endpoint_chord_scoped_estimate' ? ' (endpoint-chord estimate)' : ''}`));
    table.tBodies[0].append(row);
  }
  article.append(table);
  if (study.six_player_proxy_scenario) {
    const scenario = study.six_player_proxy_scenario;
    article.append(cell('p', `Assumption-based six-player proxy scenario: ${scenario.assumption_based_sum_m.toFixed(2)} m. Changing #11/#13 smoothing gives ${scenario.smoothing_scenario_range_m[0].toFixed(2)}–${scenario.smoothing_scenario_range_m[1].toFixed(2)} m. This is not measured team distance.`));
  }
  article.append(cell('p', `No source-supported player estimate: ${study.players_without_distance.join(', ')}.`));
  const link = document.createElement('a');
  link.href = study.viewer_path || study.court_map_path;
  link.textContent = study.viewer_path ? 'Inspect R1 frames and coverage' : 'View AoEP court map';
  article.append(link);
  return article;
}

async function load() {
  try {
    const response = await fetch('/api/case-studies/catalog', { cache: 'no-store' });
    if (!response.ok) throw new Error(`request returned ${response.status}`);
    const data = await response.json();
    if (data.schema_version !== 'local_case_studies_catalog_v1' ||
        data.case_studies?.length !== 2 || data.formal_tracking_accuracy_claim !== false ||
        data.case_studies.some(study => !Array.isArray(study.distances) ||
          study.distances.some(row => !Number.isFinite(row.approximate_distance_m) ||
            row.frames_inclusive?.length !== 2))) {
      throw new Error('invalid case-study catalog');
    }
    status.textContent = `Two bounded case studies · ${data.case_studies.reduce((sum, study) => sum + study.distances.length, 0)} approximate player-path estimates`;
    studies.replaceChildren(...data.case_studies.map(renderStudy));
  } catch (error) {
    status.textContent = `Could not load case studies: ${error.message}`;
  }
}

load();
