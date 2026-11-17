package com.danicalla04.roomfinder.ar

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.google.ar.core.Config
import com.google.ar.core.Session
import com.google.ar.core.TrackingState
import io.github.sceneview.ar.ARSceneView
import org.json.JSONArray
import kotlin.math.PI
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

class GeospatialARActivity : AppCompatActivity() {
    private data class GeoPoint(val longitude: Double, val latitude: Double)
    private data class RouteTarget(val bearing: Double)

    private lateinit var root: FrameLayout
    private lateinit var statusText: TextView
    private lateinit var directionArrow: DirectionArrowView
    private lateinit var hotelName: String
    private lateinit var route: List<GeoPoint>
    private var arView: ARSceneView? = null
    private var lastStatus = ""
    private var lastStatusAt = 0L
    private var askedPermissions = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Color.TRANSPARENT
        window.navigationBarColor = Color.BLACK
        window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_LAYOUT_STABLE or
            View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
        hotelName = intent.getStringExtra(EXTRA_HOTEL_NAME) ?: "Your hotel"
        route = parseRoute(intent.getStringExtra(EXTRA_ROUTE_COORDINATES))
        buildOverlay()

        if (route.size < 2) {
            showStatus("No road route was provided. Close AR and refresh directions.")
            return
        }
        if (!hasArCoreKey()) {
            showStatus("Add ARCORE_API_KEY to android/local.properties, then rebuild the Android app.")
            return
        }
        showPrivacyNoticeIfNeeded()
    }

    private fun buildOverlay() {
        root = FrameLayout(this)
        root.setBackgroundColor(Color.BLACK)
        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(16), dp(14), dp(16), dp(14))
            background = pillBackground(0xD91A2420.toInt(), 22)
        }
        val title = TextView(this).apply {
            text = "AR directions · $hotelName"
            setTextColor(Color.WHITE)
            textSize = 16f
            setTypeface(typeface, Typeface.BOLD)
            maxLines = 1
            ellipsize = android.text.TextUtils.TruncateAt.END
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        }
        val close = TextView(this).apply {
            text = "Close"
            textSize = 14f
            setTextColor(Color.WHITE)
            setPadding(dp(12), dp(8), dp(12), dp(8))
            background = pillBackground(0xFF315B4A.toInt(), 18)
            setOnClickListener { finish() }
        }
        header.addView(title)
        header.addView(close)
        statusText = TextView(this).apply {
            text = "Preparing AR camera…"
            textSize = 14f
            setTextColor(Color.WHITE)
            setPadding(dp(16), dp(12), dp(16), dp(12))
            background = pillBackground(0xD91A2420.toInt(), 18)
        }
        root.addView(header, FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.WRAP_CONTENT,
            Gravity.TOP or Gravity.CENTER_HORIZONTAL,
        ).apply { setMargins(dp(12), dp(42), dp(12), 0) })
        root.addView(statusText, FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.WRAP_CONTENT,
            Gravity.BOTTOM,
        ).apply { setMargins(dp(16), 0, dp(16), dp(28)) })
        directionArrow = DirectionArrowView(this).apply { visibility = View.GONE }
        root.addView(directionArrow, FrameLayout.LayoutParams(dp(104), dp(104), Gravity.CENTER))
        setContentView(root)
    }

    private fun showPrivacyNoticeIfNeeded() {
        val preferences = getSharedPreferences("geospatial_ar", MODE_PRIVATE)
        if (preferences.getBoolean("device_data_consent", false)) {
            ensurePermissions()
            return
        }
        AlertDialog.Builder(this)
            .setTitle("Location-based AR")
            .setMessage("RoomFinder uses your camera and precise location to point the on-screen arrow along the walking route. ARCore may process camera and location data to provide this feature. The camera view is not saved by RoomFinder.")
            .setNegativeButton("Cancel") { _, _ -> finish() }
            .setPositiveButton("Continue") { _, _ ->
                preferences.edit().putBoolean("device_data_consent", true).apply()
                ensurePermissions()
            }
            .setOnCancelListener { finish() }
            .show()
    }

    private fun ensurePermissions() {
        val required = arrayOf(
            Manifest.permission.CAMERA,
            Manifest.permission.ACCESS_COARSE_LOCATION,
            Manifest.permission.ACCESS_FINE_LOCATION,
        )
        if (required.all { ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED }) {
            startArSession()
        } else if (!askedPermissions) {
            askedPermissions = true
            requestPermissions(required, PERMISSIONS_REQUEST)
        }
    }

    @Deprecated("Permission callback for this small Android activity")
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != PERMISSIONS_REQUEST) return
        if (grantResults.isNotEmpty() && grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
            startArSession()
        } else {
            showStatus("Camera and precise location permissions are needed for Geospatial AR.")
        }
    }

    private fun startArSession() {
        if (arView != null || isFinishing) return
        runCatching {
            val view = ARSceneView(
                context = this,
                sharedActivity = this,
                sharedLifecycle = lifecycle,
                sessionConfiguration = { session, config ->
                    if (session.isGeospatialModeSupported(Config.GeospatialMode.ENABLED)) {
                        config.geospatialMode = Config.GeospatialMode.ENABLED
                        config.planeFindingMode = Config.PlaneFindingMode.HORIZONTAL
                    } else {
                        runOnUiThread { showStatus("This phone supports ARCore, but not Geospatial AR mode.") }
                    }
                },
                onSessionFailed = { exception ->
                    showStatus("ARCore could not start: ${exception.message ?: "check Google Play Services for AR"}")
                },
                onSessionUpdated = { session, _ -> updateGeospatial(session) },
            )
            arView = view
            root.addView(view, 0, FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT,
            ))
            showStatus("Point your camera toward the route and slowly scan nearby buildings.")
        }.onFailure { exception ->
            showStatus("AR could not start: ${exception.message ?: "check device support and permissions"}")
        }
    }

    private fun updateGeospatial(session: Session) {
        val earth = session.earth ?: return
        if (earth.trackingState != TrackingState.TRACKING) {
            val earthState = runCatching { earth.earthState.name }.getOrDefault("UNKNOWN")
            val message = when (earthState) {
                "ERROR_NOT_AUTHORIZED" -> "ARCore authorization failed. The red arrow is paused; check the ARCore API key and Android app restrictions."
                "ERROR_RESOURCE_EXHAUSTED" -> "ARCore API quota is exhausted. The red arrow is holding its last direction."
                "ERROR_APK_VERSION_TOO_OLD" -> "Update Google Play Services for AR. The red arrow is holding its last direction."
                "ERROR_GEOSPATIAL_MODE_DISABLED" -> "Geospatial mode is disabled or unsupported. The red arrow is holding its last direction."
                "ERROR_INTERNAL" -> "ARCore is reacquiring your position. The red arrow is holding its last direction."
                else -> "Waiting for precise GPS/VPS position. The red arrow will update when tracking returns."
            }
            showStatus(message)
            return
        }
        val pose = runCatching { earth.cameraGeospatialPose }.getOrNull() ?: return
        val target = findTarget(pose.latitude, pose.longitude) ?: run {
            setArrowDirection(null)
            return
        }
        @Suppress("DEPRECATION")
        val cameraHeading = pose.heading
        setArrowDirection(target.bearing - cameraHeading)
        val alignmentWeak = pose.horizontalAccuracy > MAX_HORIZONTAL_ACCURACY_METERS ||
            pose.orientationYawAccuracy > MAX_HEADING_ACCURACY_DEGREES
        if (alignmentWeak) {
            showStatus("Red arrow follows the route; alignment is approximate. Slowly scan nearby buildings.")
        } else {
            showStatus("Follow the red arrow along the route toward $hotelName")
        }
    }

    private fun findTarget(latitude: Double, longitude: Double): RouteTarget? {
        if (route.size < 2) return null
        val metersPerLatitudeDegree = 111_320.0
        val metersPerLongitudeDegree = metersPerLatitudeDegree * cos(Math.toRadians(latitude))
        if (metersPerLongitudeDegree <= 0.0) return null

        var nearestIndex = -1
        var nearestFraction = 0.0
        var nearestDistance = Double.POSITIVE_INFINITY
        for (index in 0 until route.lastIndex) {
            val start = route[index]
            val end = route[index + 1]
            val startX = (start.longitude - longitude) * metersPerLongitudeDegree
            val startY = (start.latitude - latitude) * metersPerLatitudeDegree
            val endX = (end.longitude - longitude) * metersPerLongitudeDegree
            val endY = (end.latitude - latitude) * metersPerLatitudeDegree
            val segmentX = endX - startX
            val segmentY = endY - startY
            val segmentLengthSquared = segmentX * segmentX + segmentY * segmentY
            val fraction = if (segmentLengthSquared > 0.0) {
                (-(startX * segmentX + startY * segmentY) / segmentLengthSquared).coerceIn(0.0, 1.0)
            } else {
                0.0
            }
            val closestX = startX + segmentX * fraction
            val closestY = startY + segmentY * fraction
            val distance = sqrt(closestX * closestX + closestY * closestY)
            if (distance < nearestDistance) {
                nearestDistance = distance
                nearestIndex = index
                nearestFraction = fraction
            }
        }
        if (nearestIndex < 0) return null

        val segmentStart = route[nearestIndex]
        val segmentEnd = route[nearestIndex + 1]
        val projectedPoint = GeoPoint(
            segmentStart.longitude + (segmentEnd.longitude - segmentStart.longitude) * nearestFraction,
            segmentStart.latitude + (segmentEnd.latitude - segmentStart.latitude) * nearestFraction,
        )

        var directionStart = projectedPoint
        var directionEnd = segmentEnd
        if (nearestIndex + 2 < route.size &&
            distanceMeters(
                projectedPoint.latitude,
                projectedPoint.longitude,
                segmentEnd.latitude,
                segmentEnd.longitude,
            ) < ROUTE_TURN_SWITCH_DISTANCE_METERS
        ) {
            directionStart = segmentEnd
            directionEnd = route[nearestIndex + 2]
        }
        if (distanceMeters(
                directionStart.latitude,
                directionStart.longitude,
                directionEnd.latitude,
                directionEnd.longitude,
            ) < 0.1
        ) return null
        return RouteTarget(bearingDegrees(directionStart, directionEnd))
    }

    private fun parseRoute(raw: String?): List<GeoPoint> {
        if (raw.isNullOrBlank()) return emptyList()
        return runCatching {
            val array = JSONArray(raw)
            buildList {
                for (index in 0 until array.length()) {
                    val pair = array.optJSONArray(index) ?: continue
                    if (pair.length() < 2) continue
                    val longitude = pair.optDouble(0, Double.NaN)
                    val latitude = pair.optDouble(1, Double.NaN)
                    if (longitude.isFinite() && latitude.isFinite()) add(GeoPoint(longitude, latitude))
                }
            }
        }.getOrDefault(emptyList())
    }

    private fun bearingDegrees(from: GeoPoint, to: GeoPoint): Double {
        val lat1 = Math.toRadians(from.latitude)
        val lat2 = Math.toRadians(to.latitude)
        val deltaLon = Math.toRadians(to.longitude - from.longitude)
        val y = sin(deltaLon) * cos(lat2)
        val x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(deltaLon)
        return (Math.toDegrees(atan2(y, x)) + 360.0) % 360.0
    }

    private fun distanceMeters(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val dLat = Math.toRadians(lat2 - lat1)
        val dLon = Math.toRadians(lon2 - lon1)
        val a = sin(dLat / 2).let { it * it } +
            cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) * sin(dLon / 2).let { it * it }
        return 6_371_000.0 * 2.0 * atan2(sqrt(a), sqrt(1.0 - a))
    }

    private fun hasArCoreKey(): Boolean = runCatching {
        @Suppress("DEPRECATION")
        val info = packageManager.getApplicationInfo(packageName, PackageManager.GET_META_DATA)
        !info.metaData?.getString("com.google.android.ar.API_KEY").isNullOrBlank()
    }.getOrDefault(false)

    private fun showStatus(value: String) {
        val now = System.currentTimeMillis()
        if (value == lastStatus && now - lastStatusAt < 2000L) return
        lastStatus = value
        lastStatusAt = now
        runOnUiThread { if (::statusText.isInitialized) statusText.text = value }
    }

    private fun setArrowDirection(degrees: Double?) {
        runOnUiThread {
            if (!::directionArrow.isInitialized) return@runOnUiThread
            if (degrees == null) {
                directionArrow.visibility = View.GONE
            } else {
                directionArrow.setDirection(degrees)
                directionArrow.visibility = View.VISIBLE
            }
        }
    }

    private fun pillBackground(color: Int, radiusDp: Int) = GradientDrawable().apply {
        setColor(color)
        cornerRadius = dp(radiusDp).toFloat()
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private class DirectionArrowView(context: Context) : View(context) {
        private val shape = Path()
        private val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.rgb(235, 42, 54)
            style = Paint.Style.FILL
        }
        private val outline = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.WHITE
            style = Paint.Style.STROKE
            strokeWidth = 4f * resources.displayMetrics.density
            strokeJoin = Paint.Join.ROUND
        }

        fun setDirection(degrees: Double) {
            rotation = (((degrees + 540.0) % 360.0) - 180.0).toFloat()
        }

        override fun onDraw(canvas: Canvas) {
            super.onDraw(canvas)
            val cx = width / 2f
            val cy = height / 2f
            val size = minOf(width, height) * 0.78f
            shape.reset()
            shape.moveTo(cx, cy - size * 0.5f)
            shape.lineTo(cx + size * 0.37f, cy - size * 0.04f)
            shape.lineTo(cx + size * 0.15f, cy - size * 0.04f)
            shape.lineTo(cx + size * 0.15f, cy + size * 0.43f)
            shape.lineTo(cx - size * 0.15f, cy + size * 0.43f)
            shape.lineTo(cx - size * 0.15f, cy - size * 0.04f)
            shape.lineTo(cx - size * 0.37f, cy - size * 0.04f)
            shape.close()
            canvas.drawPath(shape, outline)
            canvas.drawPath(shape, fill)
        }
    }

    override fun onDestroy() {
        arView?.destroy()
        arView = null
        super.onDestroy()
    }

    companion object {
        const val EXTRA_ROUTE_COORDINATES = "route_coordinates"
        const val EXTRA_HOTEL_NAME = "hotel_name"
        private const val PERMISSIONS_REQUEST = 441
        private const val ROUTE_TURN_SWITCH_DISTANCE_METERS = 2.0
        private const val MAX_HORIZONTAL_ACCURACY_METERS = 10.0
        private const val MAX_HEADING_ACCURACY_DEGREES = 20.0
    }
}
