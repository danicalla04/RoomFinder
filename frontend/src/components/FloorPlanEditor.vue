<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  floor: { type: Object, required: true },
  rooms: { type: Array, default: () => [] },
  busy: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false },
  selectedRoomId: { type: Number, default: null },
  roomState: { type: Function, default: () => "available" },
  roomLabel: { type: Function, default: () => "Available" },
});
const emit = defineEmits(["draw-room", "change-room", "change-floor", "edit-room", "select-room"]);
const board = ref(null);
const mode = ref("room");
const areaName = ref("");
const selectedId = ref(null);
const selectedArea = ref(null);
const draft = ref(null);
let gesture = null;

const width = computed(() => Number(props.floor.plan_width_m || 30));
const height = computed(() => Number(props.floor.plan_height_m || 20));
const floorAreas = computed(() => props.floor.areas || []);
const selectedRoom = computed(() => props.rooms.find((room) => room.id === selectedId.value));
const canDrawArea = computed(() => areaName.value.trim().length > 0 && areaName.value.trim().length <= 60);

function roomPlan(room) {
  return room.plan || { x: room.column * 5, y: room.row * 5, width: 5, height: 5, zones: [] };
}
function shownRoom(room) {
  return draft.value?.kind === "room" && draft.value.roomId === room.id
    ? { ...roomPlan(room), ...draft.value.rect }
    : roomPlan(room);
}
function shownArea(scope, roomId, index, area) {
  return draft.value?.kind === "area" && draft.value.scope === scope &&
    draft.value.roomId === roomId && draft.value.index === index
    ? { ...area, ...draft.value.rect }
    : area;
}
function styleFor(rect, parentWidth = width.value, parentHeight = height.value) {
  return {
    left: `${rect.x / parentWidth * 100}%`,
    top: `${rect.y / parentHeight * 100}%`,
    width: `${rect.width / parentWidth * 100}%`,
    height: `${rect.height / parentHeight * 100}%`,
  };
}
function pointOnBoard(event) {
  const bounds = board.value.getBoundingClientRect();
  return {
    x: Math.max(0, Math.min(width.value, (event.clientX - bounds.left) / bounds.width * width.value)),
    y: Math.max(0, Math.min(height.value, (event.clientY - bounds.top) / bounds.height * height.value)),
  };
}
function round(value) { return Math.round(value * 100) / 100; }
function rectBetween(first, second) {
  return {
    x: round(Math.min(first.x, second.x)), y: round(Math.min(first.y, second.y)),
    width: round(Math.abs(first.x - second.x)), height: round(Math.abs(first.y - second.y)),
  };
}
function capture(event) { board.value.setPointerCapture(event.pointerId); }

function selectNamedArea(scope, room, index, area) {
  selectedArea.value = { scope, roomId: room?.id ?? null, index };
  selectedId.value = room?.id ?? null;
  areaName.value = area.label || area.kind || "";
  mode.value = "select";
}
function startBoard(event) {
  if (props.readonly || props.busy || event.button !== 0) return;
  if (mode.value !== "room" && (mode.value !== "outside" || !canDrawArea.value)) return;
  const start = pointOnBoard(event);
  gesture = { kind: mode.value === "room" ? "draw-room" : "draw-floor", start };
  draft.value = { kind: gesture.kind, rect: { ...start, width: 0, height: 0 } };
  capture(event);
}
function startRoom(event, room, resize = false) {
  event.stopPropagation();
  if (props.readonly || props.busy || event.button !== 0) return;
  selectedId.value = room.id;
  selectedArea.value = null;
  const point = pointOnBoard(event);
  if (mode.value === "inside") {
    if (!room.plan || !canDrawArea.value) return;
    const plan = roomPlan(room);
    const start = { x: Math.max(0, point.x - plan.x), y: Math.max(0, point.y - plan.y) };
    gesture = { kind: "draw-inside", room, start };
    draft.value = { kind: "draw-inside", roomId: room.id, rect: { ...start, width: 0, height: 0 } };
  } else if (mode.value === "outside") {
    return;
  } else {
    gesture = { kind: resize ? "resize-room" : "move-room", room, start: point, original: { ...roomPlan(room) } };
    draft.value = { kind: "room", roomId: room.id, rect: { ...roomPlan(room) } };
  }
  capture(event);
}
function startArea(event, scope, room, index, resize = false) {
  event.stopPropagation();
  if (props.readonly || props.busy || event.button !== 0) return;
  const area = scope === "floor" ? floorAreas.value[index] : roomPlan(room).zones[index];
  selectNamedArea(scope, room, index, area);
  const point = pointOnBoard(event);
  const parent = scope === "floor" ? { x: 0, y: 0, width: width.value, height: height.value } : roomPlan(room);
  const local = { x: point.x - parent.x, y: point.y - parent.y };
  gesture = {
    kind: resize ? "resize-area" : "move-area", scope, room, index,
    start: local, original: { ...area }, parent,
  };
  draft.value = { kind: "area", scope, roomId: room?.id ?? null, index, rect: { ...area } };
  capture(event);
}
function movePointer(event) {
  if (!gesture) return;
  const point = pointOnBoard(event);
  if (gesture.kind === "draw-room" || gesture.kind === "draw-floor") {
    draft.value = { kind: gesture.kind, rect: rectBetween(gesture.start, point) };
    return;
  }
  if (gesture.kind === "draw-inside") {
    const plan = roomPlan(gesture.room);
    const local = {
      x: Math.max(0, Math.min(plan.width, point.x - plan.x)),
      y: Math.max(0, Math.min(plan.height, point.y - plan.y)),
    };
    draft.value = { kind: "draw-inside", roomId: gesture.room.id, rect: rectBetween(gesture.start, local) };
    return;
  }
  const original = gesture.original;
  const parent = gesture.parent || { width: width.value, height: height.value };
  const local = gesture.parent ? { x: point.x - parent.x, y: point.y - parent.y } : point;
  const dx = local.x - gesture.start.x;
  const dy = local.y - gesture.start.y;
  const rect = gesture.kind.startsWith("resize")
    ? { ...original,
        width: round(Math.max(1, Math.min(parent.width - original.x, original.width + dx))),
        height: round(Math.max(1, Math.min(parent.height - original.y, original.height + dy))) }
    : { ...original,
        x: round(Math.max(0, Math.min(parent.width - original.width, original.x + dx))),
        y: round(Math.max(0, Math.min(parent.height - original.height, original.y + dy))) };
  draft.value = gesture.kind.endsWith("area")
    ? { kind: "area", scope: gesture.scope, roomId: gesture.room?.id ?? null, index: gesture.index, rect }
    : { kind: "room", roomId: gesture.room.id, rect };
}
function emitAreaChange(scope, room, areas) {
  if (scope === "floor") emit("change-floor", areas);
  else emit("change-room", room, { ...roomPlan(room), zones: areas });
}
function endPointer(event) {
  if (!gesture) return;
  movePointer(event);
  const finished = gesture;
  const rect = draft.value?.rect;
  gesture = null;
  draft.value = null;
  if (!rect) return;
  if (finished.kind === "draw-room") {
    if (rect.width >= 1 && rect.height >= 1) emit("draw-room", { ...rect, zones: [] });
  } else if (finished.kind === "draw-floor" || finished.kind === "draw-inside") {
    if (rect.width < 1 || rect.height < 1) return;
    const area = { ...rect, label: areaName.value.trim() };
    if (finished.kind === "draw-floor") emitAreaChange("floor", null, [...floorAreas.value, area]);
    else emitAreaChange("room", finished.room, [...(roomPlan(finished.room).zones || []), area]);
    mode.value = "select";
  } else if (JSON.stringify(rect) !== JSON.stringify(finished.original)) {
    if (finished.kind.endsWith("room")) {
      emit("change-room", finished.room, { ...roomPlan(finished.room), ...rect });
    } else {
      const areas = finished.scope === "floor" ? floorAreas.value : roomPlan(finished.room).zones;
      emitAreaChange(finished.scope, finished.room,
        areas.map((area, index) => index === finished.index ? { ...area, ...rect } : area));
    }
  }
}
function cancelPointer() { gesture = null; draft.value = null; }
function removeArea(event, scope, room, index) {
  event.stopPropagation();
  const areas = scope === "floor" ? floorAreas.value : roomPlan(room).zones;
  emitAreaChange(scope, room, areas.filter((_, position) => position !== index));
  selectedArea.value = null;
}
function renameArea() {
  if (!selectedArea.value || !canDrawArea.value) return;
  const { scope, roomId, index } = selectedArea.value;
  const room = props.rooms.find((item) => item.id === roomId);
  const areas = scope === "floor" ? floorAreas.value : roomPlan(room).zones;
  emitAreaChange(scope, room,
    areas.map((area, position) => position === index ? { ...area, label: areaName.value.trim() } : area));
}
</script>

<template>
  <section class="floor-plan-editor">
    <div v-if="!readonly" class="plan-toolbar">
      <button type="button" :class="{ active: mode === 'room' }" @click="mode = 'room'">Draw room</button>
      <button type="button" :class="{ active: mode === 'select' }" @click="mode = 'select'">Move / resize</button>
      <label class="plan-area-name">Area name<input v-model="areaName" maxlength="60" placeholder="Kitchen, bathroom, pool..." /></label>
      <button type="button" :disabled="!canDrawArea || !selectedRoom?.plan" :class="{ active: mode === 'inside' }" @click="mode = 'inside'">Draw inside room</button>
      <button type="button" :disabled="!canDrawArea" :class="{ active: mode === 'outside' }" @click="mode = 'outside'">Draw outside room</button>
      <button type="button" :disabled="!selectedArea || !canDrawArea" @click="renameArea">Rename selected</button>
    </div>
    <p v-if="!readonly" class="muted plan-help">
      {{ mode === 'room' ? 'Drag on empty space to draw a room.' :
        mode === 'inside' ? 'Drag inside a measured room to draw the named area.' :
        mode === 'outside' ? 'Drag on empty floor space to draw the named area.' :
        'Drag a box to move it, or drag its bottom-right corner to resize it.' }}
    </p>
    <p v-if="!readonly && selectedRoom && !selectedRoom.plan" class="muted">Edit this older room and set its real size before adding an interior area.</p>
    <div
      ref="board" class="floor-plan-board"
      :style="{ aspectRatio: `${width} / ${height}` }"
      aria-label="Measured floor plan"
      @pointerdown="startBoard" @pointermove="movePointer" @pointerup="endPointer" @pointercancel="cancelPointer"
    >
      <div
        v-for="(area, index) in floorAreas" :key="`floor-${index}`"
        class="named-area shared-area" :class="{ selected: selectedArea?.scope === 'floor' && selectedArea.index === index }"
        :style="styleFor(shownArea('floor', null, index, area))"
        @pointerdown="startArea($event, 'floor', null, index)"
      >
        <span>{{ area.label || area.kind }}<small>{{ Number(shownArea('floor', null, index, area).width * shownArea('floor', null, index, area).height).toFixed(1) }} m²</small></span>
        <button v-if="!readonly" type="button" :aria-label="`Remove ${area.label || area.kind}`" @pointerdown.stop @click="removeArea($event, 'floor', null, index)">×</button>
        <i v-if="!readonly" class="area-resize" @pointerdown="startArea($event, 'floor', null, index, true)"></i>
      </div>
      <div
        v-for="room in rooms" :key="room.id"
        class="floor-plan-room" :class="[readonly ? roomState(room) : '', { selected: readonly ? selectedRoomId === room.id : selectedId === room.id, unavailable: !room.active, readonly, legacy: !room.plan }]"
        :style="styleFor(shownRoom(room))"
        role="button" tabindex="0" :aria-label="`Room ${room.number}, ${room.area} square metres`"
        @pointerdown="startRoom($event, room)" @click="readonly && emit('select-room', room)"
        @keydown.enter="emit(readonly ? 'select-room' : 'edit-room', room)"
      >
        <strong>Room {{ room.number }}</strong>
        <small>{{ room.plan ? Number(shownRoom(room).width * shownRoom(room).height).toFixed(1) : room.area }} m²</small>
        <small v-if="room.plan">{{ shownRoom(room).width }} × {{ shownRoom(room).height }} m</small>
        <small v-if="!room.plan">Approx. box</small>
        <small v-if="readonly">{{ roomLabel(room) }}</small>
        <div
          v-for="(area, index) in (room.plan?.zones || [])" :key="index"
          class="named-area room-zone" :class="{ selected: selectedArea?.scope === 'room' && selectedArea.roomId === room.id && selectedArea.index === index }"
          :style="styleFor(shownArea('room', room.id, index, area), shownRoom(room).width, shownRoom(room).height)"
          @pointerdown="startArea($event, 'room', room, index)"
        >
          <span>{{ area.label || area.kind }}<small>{{ Number(shownArea('room', room.id, index, area).width * shownArea('room', room.id, index, area).height).toFixed(1) }} m²</small></span>
          <button v-if="!readonly" type="button" :aria-label="`Remove ${area.label || area.kind} from room ${room.number}`" @pointerdown.stop @click="removeArea($event, 'room', room, index)">×</button>
          <i v-if="!readonly" class="area-resize" @pointerdown="startArea($event, 'room', room, index, true)"></i>
        </div>
        <div v-if="draft?.kind === 'draw-inside' && draft.roomId === room.id" class="named-area drafting" :style="styleFor(draft.rect, shownRoom(room).width, shownRoom(room).height)"></div>
        <button v-if="!readonly" type="button" class="room-edit" :aria-label="`Edit room ${room.number}`" @pointerdown.stop @click.stop="emit('edit-room', room)">Edit</button>
        <i v-if="!readonly" class="room-resize" @pointerdown="startRoom($event, room, true)"></i>
      </div>
      <div v-if="draft?.kind === 'draw-room'" class="floor-plan-room drafting" :style="styleFor(draft.rect)">
        <small v-if="draft.rect.width >= 1 && draft.rect.height >= 1">{{ draft.rect.width }} × {{ draft.rect.height }} m</small>
      </div>
      <div v-if="draft?.kind === 'draw-floor'" class="named-area shared-area drafting" :style="styleFor(draft.rect)">{{ areaName }}</div>
    </div>
    <p class="muted plan-scale">Plan canvas: {{ width }} m × {{ height }} m. Drawn rooms and areas are to scale. Older rooms marked “Approx. box” need their measured layout set.</p>
  </section>
</template>

<style scoped>
.floor-plan-editor { margin: 1rem 0 1.5rem; }
.plan-toolbar { display: flex; flex-wrap: wrap; align-items: end; gap: .45rem; margin-bottom: .5rem; }
.plan-toolbar button { padding: .5rem .7rem; border: 1px solid #cbd8c8; border-radius: .4rem; background: #fff; color: #315342; cursor: pointer; }
.plan-toolbar button.active { background: #214f40; color: #fff; }
.plan-toolbar button:disabled { opacity: .45; cursor: not-allowed; }
.plan-area-name { display: grid; gap: .15rem; font-size: .7rem; color: #315342; }
.plan-area-name input { width: min(16rem, 100%); padding: .45rem; border: 1px solid #cbd8c8; border-radius: .4rem; }
.plan-help, .plan-scale { margin: .5rem 0; }
.floor-plan-board { position: relative; width: 100%; overflow: hidden; border: 3px solid #315342; border-radius: .6rem; background-color: #f4f6ee; background-image: linear-gradient(#31534218 1px, transparent 1px), linear-gradient(90deg, #31534218 1px, transparent 1px); background-size: 10% 10%; touch-action: none; user-select: none; }
.floor-plan-room, .named-area { position: absolute; box-sizing: border-box; overflow: hidden; border-radius: .25rem; touch-action: none; user-select: none; }
.floor-plan-room { border: 2px solid #496a58; background: #dbead4; color: #173b2d; padding: .35rem; cursor: grab; }
.floor-plan-room.selected { border-color: #c45d31; box-shadow: inset 0 0 0 1px #c45d31; }
.floor-plan-room.unavailable { opacity: .55; }
.floor-plan-room.readonly { cursor: pointer; }
.floor-plan-room.readonly.booked { background: #f6d9cb; border-color: #9d583b; }
.floor-plan-room.readonly.capacity { background: #eee5cf; border-color: #a28955; }
.floor-plan-room.readonly.selected { background: #b7e1be; border-color: #1e7652; opacity: 1; }
.floor-plan-room.drafting { pointer-events: none; background: #a8d7b988; border-style: dashed; }
.floor-plan-room strong, .floor-plan-room small { display: block; font-size: clamp(.55rem, 1vw, .8rem); line-height: 1.2; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.named-area { display: flex; align-items: center; justify-content: center; border: 1px solid #8b765a; background: #f4dfbd; color: #5d432b; font-size: clamp(.45rem, .8vw, .7rem); cursor: grab; }
.named-area.shared-area { background: #cbe5ee; border-color: #638999; color: #254c5c; }
.named-area.selected { outline: 2px solid #c45d31; outline-offset: -2px; }
.named-area.drafting { background: #e6b87c99; border-style: dashed; pointer-events: none; }
.named-area span { display: block; overflow: hidden; text-align: center; line-height: 1.1; }
.named-area span small { display: block; font-size: inherit; }
.named-area button { position: absolute; top: 0; right: 0; border: 0; background: #fff9; cursor: pointer; line-height: 1; }
.room-edit { position: absolute; bottom: 2px; left: 2px; border: 0; border-radius: .2rem; background: #fff9; color: #173b2d; font-size: .6rem; cursor: pointer; }
.room-resize, .area-resize { position: absolute; right: 0; bottom: 0; width: 14px; height: 14px; cursor: nwse-resize; background: linear-gradient(135deg, transparent 48%, #315342 50%); }
.area-resize { width: 10px; height: 10px; }
</style>
