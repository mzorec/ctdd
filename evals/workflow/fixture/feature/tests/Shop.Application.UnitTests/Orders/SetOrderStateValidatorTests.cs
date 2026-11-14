namespace Shop.Application.UnitTests.Orders;

public sealed class SetOrderStateValidatorTests
{
    private static bool IsValid(string? note) =>
        new SetOrderStateCommandValidator()
            .Validate(new SetOrderStateCommand("A-300", SettableOrderState.Packed, note)).IsValid;

    [Fact]
    public void SetOrderStateValidator_RejectsANoteOverTheLimit()
    {
        var tooLong = new string('x', 501);
        var atLimit = new string('x', 500);

        Assert.False(IsValid(tooLong));
        Assert.True(IsValid(atLimit));
    }
}
