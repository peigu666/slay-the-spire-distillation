package example;

import basemod.BaseMod;
import basemod.interfaces.PostInitializeSubscriber;
import com.evacipated.cardcrawl.modthespire.lib.SpireInitializer;

@SpireInitializer
public class MinimalMod implements PostInitializeSubscriber {
    public MinimalMod() {
        BaseMod.subscribe(this);
    }

    public static void initialize() {
        new MinimalMod();
    }

    @Override
    public void receivePostInitialize() {
        // Register cards, relics, strings, or UI here after the base game is initialized.
    }
}
