package com.danicalla04.roomfinder;

import android.os.Bundle;

import com.danicalla04.roomfinder.ar.GeospatialARPlugin;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(GeospatialARPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
