import { useState, useEffect, useCallback } from 'react';
import { getCanvasTexture } from '@/webgl/helpers/getCanvasTexture';

export default function useCollageTexture(images, options = {}) {
    const [textureResults, setTextureResults] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    const { gap = 0, canvasHeight = 512, canvasWidth = 512, axis = 'x' } = options;

    const createTexture = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);
            const result = await getCanvasTexture({
                images,
                gap,
                canvasHeight,
                canvasWidth,
                axis,
            });
            setTextureResults(result);
        } catch (err) {
            setError(err instanceof Error ? err : new Error('Failed to create texture'));
        } finally {
            setIsLoading(false);
        }
    }, [images, gap, canvasHeight, canvasWidth, axis]);

    useEffect(() => {
        if (images.length > 0) createTexture();
    }, [images.length, createTexture]);

    return {
        texture: textureResults?.texture || null,
        dimensions: textureResults?.dimensions || null,
        isLoading,
        error,
    };
}
