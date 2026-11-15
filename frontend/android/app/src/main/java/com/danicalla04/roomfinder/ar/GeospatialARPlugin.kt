package com.danicalla04.roomfinder.ar

import android.content.Intent
import com.getcapacitor.JSArray
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin

@CapacitorPlugin(name = "GeospatialAR")
class GeospatialARPlugin : Plugin() {
    @PluginMethod
    fun start(call: PluginCall) {
        val coordinates: JSArray? = call.getArray("coordinates")
        if (coordinates == null || coordinates.length() < 2) {
            call.reject("A road route is required before opening AR directions.")
            return
        }

        val hotelName = call.getString("hotelName") ?: "Your hotel"
        val intent = Intent(activity, GeospatialARActivity::class.java).apply {
            putExtra(GeospatialARActivity.EXTRA_ROUTE_COORDINATES, coordinates.toString())
            putExtra(GeospatialARActivity.EXTRA_HOTEL_NAME, hotelName)
        }
        activity.startActivity(intent)
        call.resolve()
    }
}
